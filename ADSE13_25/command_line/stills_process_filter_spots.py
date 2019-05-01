from __future__ import absolute_import, division, print_function
from six.moves import range

import logging
import os
import math

from dxtbx.model.experiment_list import ExperimentListFactory
from dxtbx.model.experiment_list import ExperimentList

from libtbx.utils import Abort, Sorry
from libtbx.phil import parse

from dials.command_line.stills_process import control_phil_str, dials_phil_str, program_defaults_phil_str
from dials.command_line.stills_process import do_import, Script, Processor

logger = logging.getLogger('stills_process_iota')

help_message = '''
script for processing stills using IOTA-style to explore optimal spotfinding/indexing params
Currently supports the RANSAC way of selecting a consensus lattice and assigning hkl values
to bragg spots.
'''

iota_phil_str = '''
iota {
  method = off *random_sub_sampling
    .type = choice
    .help = Type of IOTA processing to be done. \
            off : No IOTA processing is done. \
            random-sub-sampling : randomly sub-sample observed bragg spots and index. Can be done multiple times. See options for random-sub-sampling if this is used.
  random_sub_sampling {
    ntrials = 50
      .type = int
      .help = Number of random sub-samples to be selected
    fraction_sub_sample = 0.8
      .type = float
      .help = fraction of sample to be sub-sampled. Should be between 0 and 1
    consensus_function = *unit_cell
      .type = choice
      .help = choose the type of consensus function to be employed for random_sub_sampling. More details \
              in the functions themselves
    show_plot = False
      .type = bool
      .help = Flag to indicate whether plots for clustering are to be displayed. Useful for debugging
    no_outlier_rejection_and_candidates_refinement=False
      .type = bool
      .help = Flag to indicate if candidate basis vectors should be refined and whether \
              outlier rejectionis needed
    finalize_method = union_and_reindex *reindex_with_known_crystal_models
      .type = choice
      .help = union_and_reindex will take union of all spots used to obtain \
              cluster (hence lattice) and then reindex with all the lattice models \
              of that cluster.\
              reindex_with_known_crystal_models will just index the spots with \
              known_orientation_indexer. Useful if clustering fails but indexing \
              succeeds in limited trials
    Z_cutoff = 1.0
      .type = float
      .help = Z-score cutoff for accepting/rejecting bragg spots based on difference between \
              fractional and integer hkl. This will be used for finalize_method = union_and_reindex
    min_indexed_spots = 16
      .type = int
      .help = minimum number of spots that should be indexed on an image by a model
    align_calc_spots_with_obs = True
      .type = bool
      .help = if True, adjusts detector distance to try minimize rcalc-robs for unrefined indexing \
              results.

  }
  include scope exafel_project.ADSE13_25.clustering.consensus_functions.clustering_iota_scope
}
'''

phil_scope = parse(control_phil_str + dials_phil_str + iota_phil_str, process_includes=True).fetch(parse(program_defaults_phil_str))


class Script_iota(Script):
    ''' Script class with functions customized for iota style processsing '''

    def __init__(self):
        """Initialise the script."""
        from dials.util.options import OptionParser
        import libtbx.load_env

        # The script usage
        usage = (
            "usage: %s [options] [param.phil] filenames" % libtbx.env.dispatcher_name
        )

        self.tag = None
        self.reference_detector = None

        # Create the parser
        self.parser = OptionParser(usage=usage, phil=phil_scope, epilog=help_message)

    def run(self):
        """Execute the script."""
        from dials.util import log
        from time import time
        from libtbx import easy_mp
        import copy

        # Parse the command line
        params, options, all_paths = self.parser.parse_args(
            show_diff_phil=False, return_unhandled=True, quick_parse=True
        )

        # Check we have some filenames
        if not all_paths:
            self.parser.print_help()
            return

        # Mask validation
        for mask_path in params.spotfinder.lookup.mask, params.integration.lookup.mask:
            if mask_path is not None and not os.path.isfile(mask_path):
                raise Sorry("Mask %s not found" % mask_path)

        # Save the options
        self.options = options
        self.params = params

        st = time()

        # Configure logging
        log.config(
            params.verbosity, info="dials.process.log", debug="dials.process.debug.log"
        )

        bad_phils = [f for f in all_paths if os.path.splitext(f)[1] == ".phil"]
        if len(bad_phils) > 0:
            self.parser.print_help()
            logger.error(
                "Error: the following phil files were not understood: %s"
                % (", ".join(bad_phils))
            )
            return

        # Log the diff phil
        diff_phil = self.parser.diff_phil.as_str()
        if diff_phil is not "":
            logger.info("The following parameters have been modified:\n")
            logger.info(diff_phil)

        for abs_params in self.params.integration.absorption_correction:
            if abs_params.apply:
                if not (
                    self.params.integration.debug.output
                    and not self.params.integration.debug.separate_files
                ):
                    raise Sorry(
                        "Shoeboxes must be saved to integration intermediates to apply an absorption correction. "
                        + "Set integration.debug.output=True, integration.debug.separate_files=False and "
                        + "integration.debug.delete_shoeboxes=True to temporarily store shoeboxes."
                    )

        self.load_reference_geometry()
        from dials.command_line.dials_import import ManualGeometryUpdater

        update_geometry = ManualGeometryUpdater(params)

        # Import stuff

        logger.info("Loading files...")
        pre_import = params.dispatch.pre_import or len(all_paths) == 1
        if pre_import:
            # Handle still imagesets by breaking them apart into multiple experiments
            # Further handle single file still imagesets (like HDF5) by tagging each
            # frame using its index

            experiments = ExperimentList()
            for path in all_paths:
                experiments.extend(do_import(path, load_models=False))

            indices = []
            basenames = []
            split_experiments = []
            for i, imageset in enumerate(experiments.imagesets()):
                assert len(imageset) == 1
                paths = imageset.paths()
                indices.append(i)
                basenames.append(os.path.splitext(os.path.basename(paths[0]))[0])
                split_experiments.append(experiments[i : i + 1])
            tags = []
            for i, basename in zip(indices, basenames):
                if basenames.count(basename) > 1:
                    tags.append("%s_%05d" % (basename, i))
                else:
                    tags.append(basename)

            # Wrapper function
            def do_work(i, item_list):
                processor = Processor_iota(
                    copy.deepcopy(params), composite_tag="%04d" % i, rank=i
                )

                for item in item_list:
                    try:
                        assert len(item[1]) == 1
                        experiment = item[1][0]
                        experiment.load_models()
                        imageset = experiment.imageset
                        update_geometry(imageset)
                        experiment.beam = imageset.get_beam()
                        experiment.detector = imageset.get_detector()
                    except RuntimeError as e:
                        logger.warning(
                            "Error updating geometry on item %s, %s"
                            % (str(item[0]), str(e))
                        )
                        continue

                    if self.reference_detector is not None:
                        from dxtbx.model import Detector

                        experiment = item[1][0]
                        imageset = experiment.imageset
                        imageset.set_detector(
                            Detector.from_dict(self.reference_detector.to_dict())
                        )
                        experiment.detector = imageset.get_detector()

                    processor.process_experiments(item[0], item[1])
                processor.finalize()

            iterable = zip(tags, split_experiments)

        else:
            basenames = [
                os.path.splitext(os.path.basename(filename))[0]
                for filename in all_paths
            ]
            tags = []
            for i, basename in enumerate(basenames):
                if basenames.count(basename) > 1:
                    tags.append("%s_%05d" % (basename, i))
                else:
                    tags.append(basename)

            # Wrapper function
            def do_work(i, item_list):
                processor = Processor_iota(
                    copy.deepcopy(params), composite_tag="%04d" % i, rank=i
                )
                for item in item_list:
                    tag, filename = item

                    experiments = do_import(filename, load_models=True)
                    imagesets = experiments.imagesets()
                    if len(imagesets) == 0 or len(imagesets[0]) == 0:
                        logger.info("Zero length imageset in file: %s" % filename)
                        return
                    if len(imagesets) > 1:
                        raise Abort(
                            "Found more than one imageset in file: %s" % filename
                        )
                    if len(imagesets[0]) > 1:
                        raise Abort(
                            "Found a multi-image file. Run again with pre_import=True"
                        )

                    try:
                        update_geometry(imagesets[0])
                        experiment = experiments[0]
                        experiment.beam = imagesets[0].get_beam()
                        experiment.detector = imagesets[0].get_detector()
                    except RuntimeError as e:
                        logger.warning(
                            "Error updating geometry on item %s, %s" % (tag, str(e))
                        )
                        continue

                    if self.reference_detector is not None:
                        from dxtbx.model import Detector

                        imageset = experiments[0].imageset
                        imageset.set_detector(
                            Detector.from_dict(self.reference_detector.to_dict())
                        )
                        experiments[0].detector = imageset.get_detector()

                    processor.process_experiments(tag, experiments)
                processor.finalize()

            iterable = zip(tags, all_paths)


        # Process the data
        # Process the data
        if params.mp.method == "mpi":
            from mpi4py import MPI

            comm = MPI.COMM_WORLD
            rank = comm.Get_rank()  # each process in MPI has a unique id, 0-indexed
            size = comm.Get_size()  # size: number of processes running in this job

            # Configure the logging
            if params.output.logging_dir is None:
                info_path = ""
                debug_path = ""
            else:
                import sys

                log_path = os.path.join(
                    params.output.logging_dir, "log_rank%04d.out" % rank
                )
                error_path = os.path.join(
                    params.output.logging_dir, "error_rank%04d.out" % rank
                )
                print("Redirecting stdout to %s" % log_path)
                print("Redirecting stderr to %s" % error_path)
                sys.stdout = open(log_path, "a", buffering=0)
                sys.stderr = open(error_path, "a", buffering=0)
                print("Should be redirected now")

                info_path = os.path.join(
                    params.output.logging_dir, "info_rank%04d.out" % rank
                )
                debug_path = os.path.join(
                    params.output.logging_dir, "debug_rank%04d.out" % rank
                )

            from dials.util import log

            log.config(params.verbosity, info=info_path, debug=debug_path)

            subset = [item for i, item in enumerate(iterable) if (i + rank) % size == 0]
            do_work(rank, subset)
        else:
            from dxtbx.command_line.image_average import splitit

            if params.mp.nproc == 1:
                do_work(0, iterable)
            else:
                result = list(
                    easy_mp.multi_core_run(
                        myfunction=do_work,
                        argstuples=list(enumerate(splitit(iterable, params.mp.nproc))),
                        nproc=params.mp.nproc,
                    )
                )
                error_list = [r[2] for r in result]
                if error_list.count(None) != len(error_list):
                    print(
                        "Some processes failed excecution. Not all images may have processed. Error messages:"
                    )
                    for error in error_list:
                        if error is None:
                            continue
                        print(error)

        # Total Time
        logger.info("")
        logger.info("Total Time Taken = %f seconds" % (time() - st))



class Processor_iota(Processor):
    ''' Processor class with functions customized for iota style processing '''

    def process_experiments(self, tag, experiments):
        if not self.params.output.composite_output:
            self.setup_filenames(tag)
        self.tag = tag
        print('MP method = ',self.params.mp.method)
        if self.params.output.experiments_filename:
            from dxtbx.model.experiment_list import ExperimentListDumper
            dump = ExperimentListDumper(experiments)
            dump.as_json(self.params.output.experiments_filename)

        # Do the processing
        try:
            self.pre_process(experiments)
        except Exception as e:
            print("Error in pre-process", tag, str(e))
            if not self.params.dispatch.squash_errors: raise
            return
        try:
            if self.params.dispatch.find_spots:
                observed = self.find_spots(experiments)
            else:
                print("Spot Finding turned off. Exiting")
                return
        except Exception as e:
            print("Error spotfinding", tag, str(e))
            if not self.params.dispatch.squash_errors: raise
            return
        try:
            # Try finding spots that are too close to each other and kick one of them out
            #import pdb; pdb.set_trace()
            obs = observed['xyzobs.px.value']
            critical_robs = 7.0
            from scitbx.matrix import col
            from annlib_ext import AnnAdaptor
            from scitbx.array_family import flex
            pop_indices = []
            xx = []
            for ii in range(len(obs)):
                for jj in range(ii+1,len(obs)):
                    robs = (col(obs[ii]) - col(obs[jj])).length()
                    xx.append(robs)
                    #print (robs)
                    if robs < critical_robs:
                        pop_indices.extend([ii,jj])
            if len(pop_indices) > 1:
                pop_indices = list(set(pop_indices))
                pop_table = [1]*len(observed)
                for ii in range(len(observed)):
                    if ii in pop_indices:
                        pop_table[ii]=0
                observed = observed.select(flex.bool(pop_table))
                from libtbx.easy_pickle import dump
                dump('filtered.pickle', observed)
                #from IPython import embed; embed(); exit()

            if self.params.dispatch.index:
                if self.params.iota.method == 'random_sub_sampling':
                    from scitbx.array_family import flex
                    len_max_indexed = -999
                    experiments_list = []
                    self.known_crystal_models=None
                    # Add an id for each strong spot observed in the image
                    observed['spot_id'] = flex.size_t(range(len(observed)))
                    # No outlier rejection or refinement should be done for the candidate basis vectors
                    outlier_rejection_flag=self.params.indexing.stills.candidate_outlier_rejection
                    refine_all_candidates_flag=self.params.indexing.stills.refine_all_candidates
                    if self.params.iota.random_sub_sampling.no_outlier_rejection_and_candidates_refinement:
                        self.params.indexing.stills.candidate_outlier_rejection=False
                        self.params.indexing.stills.refine_all_candidates=False

                    observed_samples_list = []
                    for trial in range(self.params.iota.random_sub_sampling.ntrials):
                        flex.set_random_seed(trial+1001)
                        observed_sample = observed.select(flex.random_selection(len(observed), int(len(observed)*self.params.iota.random_sub_sampling.fraction_sub_sample)))
                        try:
                            print ('IOTA: SUM_INTENSITY_VALUE',sum(observed_sample['intensity.sum.value']), ' ',trial, len(observed_sample))
                            if self.params.iota.random_sub_sampling.finalize_method == 'union_and_reindex':
                                experiments_tmp, indexed_tmp = self.index_with_iota(experiments, observed_sample)
                            elif self.params.iota.random_sub_sampling.finalize_method == 'reindex_with_known_crystal_models':
                                experiments_tmp, indexed_tmp = self.index(experiments, observed_sample)

                            experiments_list.append(experiments_tmp)
                            observed_samples_list.append(observed_sample)
                        except Exception as e:
                            print('Indexing failed for some reason', str(e))
                    #from libtbx.easy_pickle import dump,load
                    #dump('experiments_list.pickle', experiments_list)
                    #dump('observed_samples_list.pickle', observed_samples_list)
                    #exit()
                    #from libtbx.easy_pickle import load
                    #experiments_list = load('experiments_list.pickle')
                    #observed_samples_list = load('observed_samples_list.pickle')
                    #from IPython import embed; embed(); exit()
                    if self.params.iota.random_sub_sampling.consensus_function == 'unit_cell':
                        if self.params.iota.random_sub_sampling.finalize_method == 'reindex_with_known_crystal_models':
                            from exafel_project.ADSE13_25.clustering.old_consensus_functions import get_uc_consensus as get_consensus
                            known_crystal_models, clustered_experiments_list = get_consensus(experiments_list, show_plot=False, return_only_first_indexed_model=True, finalize_method=None, clustering_params=None)
                        else:
                            from exafel_project.ADSE13_25.clustering.consensus_functions import get_uc_consensus as get_consensus
                            known_crystal_models, clustered_experiments_list = get_consensus(experiments_list, show_plot=self.params.iota.random_sub_sampling.show_plot, return_only_first_indexed_model=False, finalize_method=self.params.iota.random_sub_sampling.finalize_method, clustering_params=self.params.iota.clustering)
                       # from IPython import embed; embed(); exit()
                    print ('IOTA: Finalizing consensus')
                    if self.params.iota.random_sub_sampling.finalize_method == 'reindex_with_known_crystal_models':
                        print ('IOTA: Chosen finalize method is reindex_with_known_crystal_models')
                        self.known_crystal_models = known_crystal_models
                        # Set back whatever PHIL parameter was supplied by user for outlier rejection and refinement
                        self.params.indexing.stills.candidate_outlier_rejection=outlier_rejection_flag
                        self.params.indexing.stills.refine_all_candidates=refine_all_candidates_flag
                        import pdb; pdb.set_trace()
                        experiments, indexed = self.index_with_known_orientation(experiments, observed)
                        print('fraction subsampled = %5.2f with %d indexed spots ' %(self.params.iota.random_sub_sampling.fraction_sub_sample,len(indexed)))

                    elif self.params.iota.random_sub_sampling.finalize_method == 'union_and_reindex':
                        print ('IOTA: Chosen finalize method is union_and_reindex')
                        # Take union of all spots used to index each lattice cluster
                        from dials.array_family import flex as dials_flex
                        from dxtbx.model.experiment_list import ExperimentList, Experiment
                        indexed = dials_flex.reflection_table()
                        #experiments = ExperimentList()
                        sample = {}
                        all_experimental_models = {}
                        assert len(experiments_list[0].detectors()) == 1, 'IOTA currently supports only one detector when indexing'
                        import copy
                        original_detector = copy.deepcopy(experiments_list[0].detectors()[0])
                        for idx,crystal_model in enumerate(clustered_experiments_list):
                            if crystal_model >= 0:
                                if crystal_model not in sample:
                                    sample[crystal_model] = []
                                    all_experimental_models[crystal_model] = []
                                sample[crystal_model].append(observed_samples_list[idx]['spot_id'])
                                all_experimental_models[crystal_model].append(experiments_list[idx])
                        # FIXME take out
                        all_indexed_tmp = dials_flex.reflection_table()
                        all_experiments_tmp = ExperimentList()
                        tmp_counter = 0
                        for crystal_model in sample:
                            # Need to have a minimum number of experiments for correct stats
                            # FIXME number should not be hardcoded. ideally a phil param
                            if len(all_experimental_models[crystal_model]) < 3:
                                continue
                            self.known_crystal_models = None
                            union_indices=flex.union(len(observed), iselections=sample[crystal_model])
                            union_observed = observed.select(union_indices)
                            print ('done taking unions')
                            # First index the union set with the central crystal model of the cluster
                            self.known_crystal_models = None #[known_crystal_models[crystal_model]]
                            from cctbx import crystal
                            explist_centroid = ExperimentList()
                            for i,i_expt in enumerate(experiments):
                                exp = Experiment(imageset=i_expt.imageset,
                                                 beam=i_expt.beam,
                                                 detector=i_expt.detector,
                                                 goniometer=i_expt.goniometer,
                                                 scan=i_expt.scan,
                                                 crystal=known_crystal_models[crystal_model])
                                explist_centroid.append(exp)

                            from exafel_project.ADSE13_25.indexing.indexer_iota import iota_indexer
                            reidxr = iota_indexer(union_observed, imagesets,params=self.params)
                            reidxr.calculate_fractional_hkl_from_Ainverse_q(reidxr.reflections, explist_centroid)
                            experiments_centroid = explist_centroid
                            indexed_centroid = reidxr.reflections

                            if self.params.iota.random_sub_sampling.align_calc_spots_with_obs:
                                # Move detector to bring calculated spots onto observed spots.
                                # Only done in radial direction
                                assert len(experiments_centroid.detectors()) == 1, 'aligning spots only work with one detector'
                                import copy
                                image_identifier = imagesets[0].get_image_identifier(0)
                                moved_detector = self.move_detector_to_bring_calc_spots_onto_obs(experiments_centroid.detectors()[0], experiments_centroid.beams()[0], indexed_centroid, image_identifier)
                                # Reindex everything again with new detector distance!
                                explist_centroid = ExperimentList()

                            for i,i_expt in enumerate(experiments):
                                i_expt.imageset.set_detector(moved_detector)
                                exp = Experiment(imageset=i_expt.imageset,
                                                 beam=i_expt.beam,
                                                 detector=i_expt.detector,
                                                 goniometer=i_expt.goniometer,
                                                 scan=i_expt.scan,
                                                 crystal=known_crystal_models[crystal_model])
                                explist_centroid.append(exp)

                                from exafel_project.ADSE13_25.indexing.indexer_iota import iota_indexer
                                reidxr = iota_indexer(union_observed, imagesets,params=self.params)
                                reidxr.calculate_fractional_hkl_from_Ainverse_q(reidxr.reflections, explist_centroid)
                                experiments_centroid = explist_centroid
                                indexed_centroid = reidxr.reflections

                            indexed_centroid['id'].set_selected(flex.size_t(range(len(indexed_centroid))), crystal_model)
                            print ('finished evaluating centroid indexing results for crystal model ',crystal_model)
                            # Now index with each each experimental model for each of the unioned observations
                            dh_list = flex.double()
                            failed_model_counter = 0
                            hkl_all_values = {}
                            for obs in all_experimental_models[crystal_model]:
                                try:
                                    explist = ExperimentList()
                                    self.known_crystal_models = None #[obs.crystals()[0]]

                                    # Make sure the crystal is rotated using the best_similarity_transformation
                                    # with respect to the centroid model. Otherwise dh values will be junk
                                    from cctbx_orientation_ext import crystal_orientation
                                    cryst_ref_ori = crystal_orientation(explist_centroid.crystals()[0].get_A(), True)
                                    cryst_tmp_ori = crystal_orientation(obs.crystals()[0].get_A(), True)
                                    best_similarity_transform = cryst_tmp_ori.best_similarity_transformation(
                                      other = cryst_ref_ori, fractional_length_tolerance = 10.00,
                                      unimodular_generator_range=1)
                                    cryst_tmp_ori_best=cryst_tmp_ori.change_basis(best_similarity_transform)
                                    obs.crystals()[0].set_A(cryst_tmp_ori_best.reciprocal_matrix())


                                    for i, i_expt in enumerate(experiments):
                                        exp=Experiment(imageset=i_expt.imageset, 
                                                       beam=i_expt.beam,
                                                       detector=i_expt.detector, 
                                                       goniometer=i_expt.goniometer,
                                                       scan=i_expt.scan,
                                                       crystal=obs.crystals()[0])
                                        explist.append(exp)
                                    reidxr = iota_indexer(union_observed, imagesets,params=self.params)
                                    reidxr.calculate_fractional_hkl_from_Ainverse_q(reidxr.reflections, explist)
                                    experiments_tmp = explist
                                    indexed_tmp = reidxr.reflections
                                    # FIXME take out

                                    indexed_tmp['id'].set_selected(flex.size_t(range(len(indexed_tmp))),tmp_counter)
                                    all_indexed_tmp.extend(indexed_tmp)
                                    all_experiments_tmp.append(exp)
                                    tmp_counter +=1

                                    # find dh = |h_frac - h_centroid|
                                    indexed_idxlist = [idx for idx,elem in enumerate(indexed_tmp['xyzobs.mm.value'])
                                                       if elem in indexed_centroid['xyzobs.mm.value']]
                                    dh_list_tmp = flex.double()
                                    for idx in indexed_idxlist:
                                        centroid_list_idx = list(indexed_centroid['xyzobs.mm.value']).index(indexed_tmp['xyzobs.mm.value'][idx])
                                        x = indexed_centroid['miller_index'][centroid_list_idx]
                                        y = indexed_tmp['fractional_miller_index'][idx]
                                        if indexed_centroid['miller_index'][centroid_list_idx] != indexed_tmp['miller_index'][idx]:
                                            continue
                                        if indexed_centroid['miller_index'][centroid_list_idx] not in hkl_all_values:
                                            hkl_all_values[indexed_centroid['miller_index'][centroid_list_idx]] = flex.vec3_double()
                                        hkl_all_values[indexed_centroid['miller_index'][centroid_list_idx]].append(y)
                                        if x == (0,0,0): continue
                                    print ('finished evaluating dh_list for crystal model ',crystal_model)
                                except Exception as e:
                                    print ('Reindexing with candidate lattices on union set failed', str(e))
                            # Get a sense of the variability in dh. Assign Z-score cutoff from there
                            try:
                                Z_cutoff = self.params.iota.random_sub_sampling.Z_cutoff
                                # Now go through the spots indexed by the cluster center and reject if dh greater than Z_cutoff
                                indexed_spots_idx = []
                                for ii,refl in enumerate(indexed_centroid):
                                    dh = flex.double([refl['miller_index'][0]-refl['fractional_miller_index'][0],
                                                  refl['miller_index'][1]-refl['fractional_miller_index'][1],
                                                  refl['miller_index'][2]-refl['fractional_miller_index'][2]]).norm()
                                    hfrac,kfrac,lfrac = hkl_all_values[refl['miller_index']].parts()
                                    # FIXME arbitrary cutoff: if not enough datapoints, cant do a statistical analysis
                                    if len(list(hfrac)) < 3:
                                        continue
                                    dh_cutoff = hfrac.sample_standard_deviation()*hfrac.sample_standard_deviation()+ \
                                                kfrac.sample_standard_deviation()*kfrac.sample_standard_deviation()+ \
                                                lfrac.sample_standard_deviation()*lfrac.sample_standard_deviation()
                                    dh_cutoff = math.sqrt(dh_cutoff)*Z_cutoff
                                    panel = experiments_centroid.detectors()[0][0]
                                    beam = experiments_centroid.beams()[0]
                                    resolution = panel.get_resolution_at_pixel(beam.get_s0(),refl['xyzobs.px.value'][0:2])
                                    print ('MILLER_INDEX_DH_STATS', refl['miller_index'], ' ',dh,' ',dh_cutoff,' ',resolution)

                                    #self.refine(all_experiments_tmp, all_indexed_tmp)
                                    #from IPython import embed; embed(); exit()
                                    #print ('DH = %12.7f and CUTOFF = %12.7f'%(dh, dh_cutoff))
                                    if dh < dh_cutoff and refl['miller_index'] != (0,0,0):
                                        indexed_spots_idx.append(ii)
                                # Make sure the number of spots indexed by a model is above a threshold
                                if len(indexed_centroid.select(flex.size_t(indexed_spots_idx))) > self.params.iota.random_sub_sampling.min_indexed_spots:
                                    indexed.extend(indexed_centroid.select(flex.size_t(indexed_spots_idx)))
                                    # Need to append properly
                                    for iexpt,expt in enumerate(experiments_centroid):
                                        print ('APPENDING EXPERIMENT = ',crystal_model,iexpt)
                                        # If detector was moved to align calculated spots with observed then
                                        # restore the original distance i.e detector model
                                        # Setting it in both imageset and detector as not sure which one is used downstream
                                        if self.params.iota.random_sub_sampling.align_calc_spots_with_obs:
                                            expt.imageset.set_detector(original_detector)
                                            expt.detector = original_detector
                                        experiments.append(expt)

                            except Exception as e:
                                print ('dh_list calculation and outlier rejection failed',str(e))

                        # Make sure crytal model numbers are in sequence, example 0,1,2 instead of 0,2,3
                        # when model 1 was not used for consensus part. Otherwise refine won't work
                        max_id = flex.max(indexed['id'])
                        original_ids = []
                        for iid in range(0,max_id+1):
                            if len(indexed.select(indexed['id']==iid)) != 0:
                                original_ids.append(iid)

                        for ii,iid in enumerate(original_ids):
                            indexed['id'].set_selected(indexed['id'] == iid,ii)
                        # Set back whatever PHIL parameter was supplied by user for outlier rejection and refinement
                        self.params.indexing.stills.candidate_outlier_rejection=outlier_rejection_flag
                        self.params.indexing.stills.refine_all_candidates=refine_all_candidates_flag
                        # Perform refinement and outlier rejection
                        from exafel_project.ADSE13_25.refinement.iota_refiner import iota_refiner
                        refiner=iota_refiner(experiments, indexed, imagesets,self.params)
                        experiments,indexed = refiner.run_refinement_and_outlier_rejection()

                    try:
                        experiments,indexed = self.refine(experiments, indexed)
                    except Exception as e:
                        print("Error refining", tag, str(e))
                        if not self.params.dispatch.squash_errors: raise
                        return
                    try:
                        if self.params.dispatch.integrate:
                            integrated = self.integrate(experiments, indexed)
                        else:
                            print("Integration turned off. Exiting")
                            return
                    except Exception as e:
                        print("Error integrating", tag, str(e))
                        if self.params.dispatch.squash_errors: raise
                        return
            else:
                print("IOTA based Indexing turned off. Exiting")
                return
        except Exception as e:
            print("Couldnt index using IOTA ", tag, str(e))
            if not self.params.dispatch.squash_errors: raise
            return


    def index(self, experiments, reflections):
        from dials.algorithms.indexing.indexer import indexer_base
        from time import time
        import copy

        st = time()

        logger.info("*" * 80)
        logger.info("Indexing Strong Spots")
        logger.info("*" * 80)

        params = copy.deepcopy(self.params)
        # don't do scan-varying refinement during indexing
        params.refinement.parameterisation.scan_varying = False

        if hasattr(self, "known_crystal_models"):
            known_crystal_models = self.known_crystal_models
        else:
            known_crystal_models = None

        if params.indexing.stills.method_list is None:
            idxr = indexer_base.from_parameters(
                reflections,
                experiments,
                known_crystal_models=known_crystal_models,
                params=params,
            )
            idxr.index()
        else:
            indexing_error = None
            for method in params.indexing.stills.method_list:
                params.indexing.method = method
                try:
                    idxr = indexer_base.from_parameters(
                        reflections, experiments, params=params
                    )
                    idxr.index()
                except Exception as e:
                    logger.info("Couldn't index using method %s" % method)
                    if indexing_error is None:
                        if e is None:
                            e = Exception("Couldn't index using method %s" % method)
                        indexing_error = e
                else:
                    indexing_error = None
                    break
            if indexing_error is not None:
                raise indexing_error

        indexed = idxr.refined_reflections
        experiments = idxr.refined_experiments

        if known_crystal_models is not None:
            from dials.array_family import flex

            filtered = flex.reflection_table()
            for idx in set(indexed["miller_index"]):
                sel = indexed["miller_index"] == idx
                if sel.count(True) == 1:
                    filtered.extend(indexed.select(sel))
            logger.info(
                "Filtered duplicate reflections, %d out of %d remaining"
                % (len(filtered), len(indexed))
            )
            print(
                "Filtered duplicate reflections, %d out of %d remaining"
                % (len(filtered), len(indexed))
            )
            indexed = filtered

        logger.info("")
        logger.info("Time Taken = %f seconds" % (time() - st))
        return experiments, indexed


    def index_with_iota(self, experiments, reflections):
        from exafel_project.ADSE13_25.indexing.indexer_iota import iota_indexer
        from time import time
        import copy
        st = time()

        logger.info('*' * 80)
        logger.info('Indexing Strong Spots')
        logger.info('*' * 80)

        imagesets=experiments.imagesets()

        params = copy.deepcopy(self.params)
        # don't do scan-varying refinement during indexing
        params.refinement.parameterisation.scan_varying = False

        if hasattr(self, 'known_crystal_models'):
            known_crystal_models = self.known_crystal_models
        else:
            known_crystal_models = None

        if params.indexing.stills.method_list is None:
            idxr = iota_indexer.from_parameters(
              reflections, imagesets, known_crystal_models=known_crystal_models,
              params=params)
            idxr.index()
        else:
            indexing_error = None
            for method in params.indexing.stills.method_list:
                params.indexing.method = method
                try:
                    idxr = iota_indexer.from_parameters(
                      reflections, imagesets,
                      params=params)
                    idxr.index()
                except Exception as e:
                    logger.info("Couldn't index using method %s"%method)
                    if indexing_error is None:
                        if e is None:
                            e = Exception("Couldn't index using method %s"%method)
                        indexing_error = e
                else:
                    indexing_error = None
                    break
            if indexing_error is not None:
                raise indexing_error

        indexed = idxr.reflections
        experiments = idxr.experiments

        if known_crystal_models is not None:
            from dials.array_family import flex
            filtered = flex.reflection_table()
            for idx in set(indexed['miller_index']):
                sel = indexed['miller_index'] == idx
                if sel.count(True) == 1:
                    filtered.extend(indexed.select(sel))
            logger.info("Filtered duplicate reflections, %d out of %d remaining"%(len(filtered),len(indexed)))
            print("Filtered duplicate reflections, %d out of %d remaining"%(len(filtered),len(indexed)))
            indexed = filtered

        logger.info('')
        logger.info('Time Taken = %f seconds' % (time() - st))
        return experiments, indexed

    def move_detector_to_bring_calc_spots_onto_obs(self, detector, beam, indexed,image_identifier):
        ''' Function moves detector to ensure that radially the gap between rcalc and robs is minimized
            calculated for each spot using dnew = ((robs-r0)/(rcal-r0))*d  and then mean is taken of dnew values
            Code only works for a single detector right now. Multiple detectors will fail'''
        import copy
        from scitbx.matrix import col
        from scitbx.array_family import flex
        moved_detector = copy.deepcopy(detector)
        dnew = flex.double() # list to store all the dnew values
        for ii in range(len(indexed)):
            panel_num = indexed[ii]['panel']
            panel = detector[panel_num]
            r0 = col(panel.get_ray_intersection(beam.get_s0()))  # beam center
            D = panel.get_origin()[-1]
            rcal = col(indexed[ii]['xyzcal.mm'][0:2]) - r0 #- col(panel.get_origin()[0:2])
            robs = col(indexed[ii]['xyzobs.mm.value'][0:2]) - r0 #- col(panel.get_origin()[0:2])
            dnew.append((robs.length()/rcal.length())*D)
        #from IPython import embed; embed(); exit()

        new_distance = flex.mean(dnew)
        print ('NEW_DET_DISTANCE ',new_distance)
        for panel in moved_detector:
            orix,oriy,oriz = panel.get_origin()
            new_origin = tuple((orix,oriy,new_distance))
            panel.set_frame(panel.get_fast_axis(), panel.get_slow_axis(), new_origin )
        return moved_detector



    def index_with_known_orientation(self, experiments, reflections):
        ''' Copy of the index function from stills_process to force IOTA to use stills_indexer during known_orientation '''
        from dials.algorithms.indexing.stills_indexer import stills_indexer
        from time import time
        import copy
        st = time()

        imagesets = experiments.imagesets()

        params = copy.deepcopy(self.params)
        # don't do scan-varying refinement during indexing
        params.refinement.parameterisation.scan_varying = False

        if hasattr(self, 'known_crystal_models'):
            known_crystal_models = self.known_crystal_models
        else:
            known_crystal_models = None
        if params.indexing.stills.method_list is None:
            idxr = stills_indexer.from_parameters(
              reflections, experiments , known_crystal_models=known_crystal_models,
              params=params)
            idxr.index()
        else:
            indexing_error = None
            for method in params.indexing.stills.method_list:
                params.indexing.method = method
                try:
                    idxr = stills_indexer.from_parameters(
                      reflections, experiments,
                      params=params)
                    idxr.index()
                except Exception as e:
                    logger.info("Couldn't index using method %s"%method)
                    if indexing_error is None:
                        if e is None:
                            e = Exception("Couldn't index using method %s"%method)
                        indexing_error = e
                else:
                    indexing_error = None
                    break
            if indexing_error is not None:
                raise indexing_error

        indexed = idxr.refined_reflections
        experiments = idxr.refined_experiments

        if known_crystal_models is not None:
            from dials.array_family import flex
            filtered = flex.reflection_table()
            for idx in set(indexed['miller_index']):
                sel = indexed['miller_index'] == idx
                if sel.count(True) == 1:
                    filtered.extend(indexed.select(sel))
            print("Filtered duplicate reflections, %d out of %d remaining"%(len(filtered),len(indexed)))
            indexed = filtered

        return experiments, indexed



if __name__ == '__main__':
    from dials.util import halraiser
    try:
        script = Script_iota()
        script.run()
    except Exception as e:
        halraiser(e)
