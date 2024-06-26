from __future__ import absolute_import,print_function, division
import sys, os, math
from iotbx.detectors.cspad_detector_formats import reverse_timestamp
from matplotlib import pyplot as plt
from dials.array_family import flex
from libtbx.utils import Sorry

message = '''
Code for calculating analytics for indexing
Provides information on
1. # of hits
2. # of indexed images
3. Timing for indexing and indexing attempts
4. Unit cell distribution and plots
5. RMSD of calculated vs observed bragg spots

Run code like libtbx.python indexing_analytics.py params.phil

Also has MPI capability if you are handling a large number of files
Run it like mpirun -n nproc libtbx.python indexing_analytics.py params.phil

'''

from libtbx.phil import parse
phil_scope = parse('''
  input_path = None
    .multiple = True
    .type = path
    .help = input_path should be like that used at LCLS i.e full path to run_number/trial_rg \
            Assumes folder structure \
            Input Path    -----> out -----> debug folder \
                          -----> pickle and json files \
                          -----> stdout \
            You can specificy multiple paths. In that case, the unit cells and RMSD info will be \
            only for the common set of images indexed
  num_nodes = 32
    .type = int
    .help = Number of nodes used to do data processing. Used in timing information
  num_cores = None
    .type = int
    .help = Number of cores used to do data processing. Used in timing information. If provided, will \
            be used instead of num_cores_per_node. Useful for cases where an entire node was not used
  num_cores_per_node = 68
    .type = int
    .help = Number of cores per node in the machine (default is for Cori KNL)
  out_logfile = None
    .type = str
    .help = logfile from NERSC (like slurm-xxxx) or elsewhere. Needed for picking up timing info
  mpi = False
    .type = bool
    .help = If True, mpi can be used for running the program
  write_out_timings = False
    .type = bool
    .help = If True, writes out timing info for each frame to a file. MPI writes out for each rank separately
  string_to_search_for = IOTA_XTC_SingleRank_TimeElapsed
    .type = str
    .help = string to search for for timing information regarding an xtc_process job
  show_plot = False
   .type = bool
   .help = Flag to determine if unit_cell plots should be shown
  indexing_time_cutoff = None
    .type = float
    .help = Maximum time that indexing of a certain image should take (in seconds). If this is set, \
            one can get the list of timestamps that exceed this cutoff
  wall_time = None
    .type = float
    .help = wall time in seconds taken for job to finish. This can be used in lieu of out_logfile option for getting timing option \
            If this and out_logfile is supplied, this takes precedence
  ts_from_cbf = False
    .type = bool
    .help = If true, gets timestamps indexed from name of cbf files. Much faster than reading in json files one by one
''')

def params_from_phil(args, phil_scope=phil_scope):
  user_phil = []
  for arg in args:
    if os.path.isfile(arg):
      user_phil.append(parse(file_name=arg))
    else:
      try:
        user_phil.append(parse(arg))
      except Exception as e:
        raise Sorry("Unrecognized argument: %s"%arg)
  params = phil_scope.fetch(sources=user_phil).extract()
  return params

def add_step(step, duration):
  step = step.strip()
  if step.endswith("_start"):
    step = "_".join(step.split('_')[:-1])
  if any([s in step for s in ['_ok_','_failed_']]):
    step = "_".join(step.split('_')[:-1])
  if 'not_enough_spots' in step:
    step = "_".join(step.split('_')[:-1])

  if step not in steps_d:
    steps_d[step] = []
  steps_d[step].append(duration)


def run(params, root, common_set=None):
  iterable = []
  iterable2 = []
  debug_root = os.path.join(root, 'debug')
  print ('start appending')
  for filename in os.listdir(debug_root):
    if os.path.splitext(filename)[1] != ".txt": continue
    iterable.append(filename)
  for filename in os.listdir(root):
    if 'refined_experiments' not in os.path.splitext(filename)[0] or os.path.splitext(filename)[1] != ".json": continue
    iterable2.append(filename)
  print ('done appending')
  #if command_line.options.mpi:
  if params.mpi:
    try:
      from mpi4py import MPI
    except ImportError:
      raise Sorry("MPI not found")
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    print (rank, size)
    # get hits and indexing info
    iterable = [iterable[i] for i in range(len(iterable)) if (i+rank)%size == 0]
    results = get_hits_and_indexing_stats(iterable, debug_root,rank)
    results = comm.gather(results, root=0)
    # Now get uc and rmsd info
    iterable2 = [iterable2[i] for i in range(len(iterable2)) if (i+rank)%size == 0]
    results2 = get_uc_and_rmsd_stats(iterable2, root,rank=rank,common_set=common_set)
    results2 = comm.gather(results2, root=0)
    if rank != 0: return
  else:
    results = [get_hits_and_indexing_stats(iterable, debug_root)]
    results2 = [get_uc_and_rmsd_stats(iterable2, root, rank=0, common_set=common_set)]
  # Now evaulate summary statistics
  print ('Now evaluating summary statistics')
  n_hits = 0
  n_idx = 0
  t_idx = 0
  t_idx_success = 0
  all_idx_cutoff_time_exceeded_event = []
  total_xray_events = 0
  total_images_analyzed = 0
  for ii,r in enumerate(results):
    n_hits += r[0]
    n_idx += r[1]
    t_idx += r[2]
    t_idx_success += r[3]
    all_idx_cutoff_time_exceeded_event.extend(r[4])
    total_xray_events += r[5]
    total_images_analyzed += r[6]
  # Write out the cutoff time exceeded events in a format that xtc_process.py can interpret for skipping events
  if indexing_time_cutoff is not None:
    fts = open('timestamps_to_skip.dat','w')
    for evt in all_idx_cutoff_time_exceeded_event:
      fts.write('psanagpu999,%s,%s,fail\n'%(evt,evt))
    fts.close()
  node_hours = None
  core_hours = None
  if out_logfile is not None and wall_time is None:
    total_time = []
    run_number = int(os.path.abspath(root).strip().split('/')[-3][1:])
    print (run_number)
    with open(out_logfile, 'r') as flog:
      for line in flog:
        if string_to_search_for in line:
          ax = line.split()
          if int(ax[-1]) == run_number:
            total_time.append(float(ax[1]))
    node_hours = max(total_time)*num_nodes/3600.0
    if num_cores is not None:
      core_hours = max(total_time)*num_cores/3600.0
    else:
      core_hours = max(total_time)*num_nodes*num_cores_per_node/3600.0

  if wall_time is not None:
    node_hours = wall_time*num_nodes/3600.0
    if num_cores is not None:
      core_hours = wall_time*num_cores/3600.0
    else:
      core_hours = wall_time*num_nodes*num_cores_per_node/3600.0

  all_uc_a = flex.double()
  all_uc_b = flex.double()
  all_uc_c = flex.double()
  all_uc_alpha = flex.double()
  all_uc_beta = flex.double()
  all_uc_gamma = flex.double()
  dR = flex.double()
  info_list = []
  info = []
  for ii,r in enumerate(results2):
    all_uc_a.extend(r[0])
    all_uc_b.extend(r[1])
    all_uc_c.extend(r[2])
    all_uc_alpha.extend(r[3])
    all_uc_beta.extend(r[4])
    all_uc_gamma.extend(r[5])
    dR.extend(r[6])
    if show_plot:
      for jj,aa in enumerate(r[0]):
        info.append({'a':r[0][jj],
                          'b':r[1][jj],
                          'c':r[2][jj],
                          'alpha':r[3][jj],
                          'beta':r[4][jj],
                          'gamma':r[5][jj],
                          'n_img':0})
  info_list.append(info)
  n_lattices = len(all_uc_a)
  # Now print out all relevant statistics
  if True:
    print ('-'*80)
    print ('|'+' '*80+'|\n'+'|'+ ' '*20 + 'Analytics Package for Indexing'+' '*30+'|\n|'+' '*80+'|')
    print ('-'*80)
    print ('Getting stats for data in : ',root)
    print ('====================== Indexing and Timing Statistics ============================')
    print ('Total number of X-ray events = ', total_xray_events)
    print ('Total number of images analyzed = ', total_images_analyzed)
    print ('Number of Hits = ', n_hits)
    print ('Number of images successfully indexed = ', n_idx)
    if common_set is None:
      print ('Number of lattices = ', n_lattices)
    else:
      print ('Number of common lattices', n_lattices)
    print ('Total time spent in indexing (hrs) = ',t_idx)
    print ('Time spent in indexing successfully (core-hrs) = ', t_idx_success)
    print ('Average time spent indexing (core-secs) = ', 3600*t_idx/n_hits)
    print ('Average time spent indexing successfully (core-secs) = ', 3600*t_idx_success/n_idx)
    if node_hours is not None:
      print ('Total Node-hours with %d nodes = %.2f (hrs)'%(num_nodes, node_hours))
      print ('% core utilization i.e (total indexing time)/(total core-hrs) = ', 100.0*t_idx/core_hours)
    if common_set is None:
      print ('====================== Unit Cell & RMSD Statistics ============================')
    else:
      print ('====================== Unit Cell & RMSD Statistics from Common Set ============================')
    print ('a-edge (A) : %.2f +/- %.2f' % (flex.mean(all_uc_a),flex.mean_and_variance(all_uc_a).unweighted_sample_standard_deviation()))
    print ('b-edge (A) : %.2f +/- %.2f' % (flex.mean(all_uc_b),flex.mean_and_variance(all_uc_b).unweighted_sample_standard_deviation()))
    print ('c-edge (A) : %.2f +/- %.2f' % (flex.mean(all_uc_c),flex.mean_and_variance(all_uc_c).unweighted_sample_standard_deviation()))
    print ('alpha (deg) : %.2f +/- %.2f' % (flex.mean(all_uc_alpha),flex.mean_and_variance(all_uc_alpha).unweighted_sample_standard_deviation()))
    print ('beta (deg) : %.2f +/- %.2f' % (flex.mean(all_uc_beta),flex.mean_and_variance(all_uc_beta).unweighted_sample_standard_deviation()))
    print ('gamma (deg) : %.2f +/- %.2f' % (flex.mean(all_uc_gamma),flex.mean_and_variance(all_uc_gamma).unweighted_sample_standard_deviation()))
    print ('Total RMSD i.e calc - obs for Bragg spots (um) = ', 1000.0*math.sqrt(dR.dot(dR)/len(dR)))
  print ('-'*80)
  if show_plot:
    import xfel.ui.components.xfel_gui_plotter as pltr
    plotter = pltr.PopUpCharts()
    plotter.plot_uc_histogram(
      info_list=info_list,
      legend_list=['combined'],
      iqr_ratio=None)
    plotter.plt.show()


def get_hits_and_indexing_stats(filenames, debug_root,rank=0):
  print ('starting hits_and_indexing_stats', rank)
  num_of_xray_events = 0
  num_of_images_analyzed = 0
  hits = []
  events_list = []
  indexing_time = {}
  indexing_time_all = {} # Both for failed and successful indexing trials
  current_ts = ""
  current_reverse_ts = ""
  prev_step = ""
  prev_time = None
  for filename in filenames:
    with open(os.path.join(debug_root, filename)) as logfile:
      for line in logfile:
        try:
          if line == '\n': continue
          hostname, ts, now, status, step = line.strip().split(',')
        except ValueError as e:
          print (line); raise
        now_s, now_ms = reverse_timestamp(now)
        now = now_s + (1e-3 * now_ms)
        if step.strip() == 'spotfind_start':
          num_of_images_analyzed +=1
        if step.strip() == 'start':
          num_of_xray_events +=1
          curr_ts, curr_ms = reverse_timestamp(ts)
          current_reverse_ts = curr_ts + (1e-3*curr_ms)
        #if '2018-05-01T14:50Z21.976' == ts:
        #  print (line + 'THIS MIGHT BE A DUPLICATE\n')
          events_list.append(ts)
          #if prev_time is not None:
            #print (prev_step.strip(), "took", now - prev_time, "seconds")
            #add_step(prev_step, now-prev_time)
          #else:
            #print (prev_step.strip(), "took", now - prev_time, "seconds")
          #add_step(prev_step, now-prev_time)
        if prev_step.strip() == 'index_start':
          indexing_time_all[ts] = now-prev_time
        if step.strip() == 'index_start':
          hits.append(ts)
        if step.strip() == 'refine_start':
          indexing_time[ts]=now-prev_time
          #print ('DEBUG',prev_step, step, now,prev_time, ts)
        current_ts = ts
        prev_step = step
        prev_time = now
#print steps_d.keys()
#print indexing_time.keys()
#print len(hits)
  total_idx_time=0
  idx_cutoff_time_exceeded_event = []
  for event in indexing_time.keys():
#  print event, indexing_time[event]
    total_idx_time +=indexing_time[event]

  recorded_hits = []
  idx_attempt_time = []
  idx_successful_time = []

  if params.write_out_timings:
    fout = open('indexing_timing_' + str(rank)+'.dat','w')
    fout.write('Event Number             hits       indexed         t_indexed              t_indexed_attempted  \n' )
  for ii,event in enumerate(events_list):
    if event in hits:
      is_hit=1
      if event not in recorded_hits:
        recorded_hits.append(event)
      else:
        if debug_mode:
          print ('Duplicate Event ? = ', event)
    else:
      is_hit=0
    if event in indexing_time:
      is_idx=1
      t_idx=indexing_time[event]
      idx_successful_time.append(t_idx)
      assert event in indexing_time_all, 'Event not present in indexing_time_all'
      t_idx2 = indexing_time_all[event]
      idx_attempt_time.append(t_idx2)
    elif event in indexing_time_all:
      is_idx=0.5
      assert event not in indexing_time, 'Event should not be present in indexing_time'
      t_idx=0.0
      t_idx2 = indexing_time_all[event]
      idx_attempt_time.append(t_idx2)
      if t_idx2 > indexing_time_cutoff:
        idx_cutoff_time_exceeded_event.append(event)
    else:
      is_idx=0
      t_idx=0.0
      t_idx2 =0.0
    if write_out_timings:
      fout.write('%s  %3.1f  %3.1f  %12.7f  %12.7f\n' %(event, is_hit, is_idx, t_idx, t_idx2))

  if write_out_timings:
    fout.close()
  return (len(hits), len(idx_successful_time), sum(idx_attempt_time)/3600.0, sum(idx_successful_time)/3600.0, idx_cutoff_time_exceeded_event, num_of_xray_events, num_of_images_analyzed)

# Extract timing information from log file
def get_uc_and_rmsd_stats(filenames, root, rank=0, common_set=None):
  print ('Getting unit cell information')
  # Unit cell and RMSD statistics for that run
  all_uc_a = flex.double()
  all_uc_b = flex.double()
  all_uc_c = flex.double()
  all_uc_alpha = flex.double()
  all_uc_beta = flex.double()
  all_uc_gamma = flex.double()
  dR = flex.double()

  from dxtbx.model.experiment_list import ExperimentListFactory
  from dials.algorithms.refinement.prediction.managed_predictors import ExperimentsPredictorFactory
  from libtbx.easy_pickle import load
  from scitbx.matrix import col
  if common_set is not None:
    print ('Using %d common set images to report unit cell and RMSD statistics'%(len(common_set)))
  for filename in filenames:
    fjson=os.path.join(root, filename)
    experiments = ExperimentListFactory.from_json_file(fjson, check_format=False)
    expt_id_common = []
    for ii,crystal in enumerate(experiments.crystals()):
      if common_set is not None:
        cbf_now = experiments[ii].imageset.get_image_identifier(0).split('/')[-1]
        if cbf_now not in common_set: continue
        expt_id_common.append(ii)
      all_uc_a.append(crystal.get_unit_cell().parameters()[0])
      all_uc_b.append(crystal.get_unit_cell().parameters()[1])
      all_uc_c.append(crystal.get_unit_cell().parameters()[2])
      all_uc_alpha.append(crystal.get_unit_cell().parameters()[3])
      all_uc_beta.append(crystal.get_unit_cell().parameters()[4])
      all_uc_gamma.append(crystal.get_unit_cell().parameters()[5])
    fpickle = os.path.join(root, filename.split('refined_experiments')[0]+'indexed.pickle')
    reflections = load(fpickle)
    ref_predictor = ExperimentsPredictorFactory.from_experiments(experiments, force_stills=experiments.all_stills())
    reflections = ref_predictor(reflections)
    for refl in reflections:
      if common_set is not None:
        if refl['id'] not in expt_id_common: continue
      dR.append((col(refl['xyzcal.mm']) - col(refl['xyzobs.mm.value'])).length())
  return all_uc_a, all_uc_b, all_uc_c, all_uc_alpha, all_uc_beta, all_uc_gamma, dR

def get_common_set(roots, ts_from_cbf=False):
  ''' Function to get common set of images indexed in multiple folders. Based on CBF filenames 
      ts_from_cbf if True is much faster than reading from json files'''
  from dxtbx.model.experiment_list import ExperimentListFactory
  cbf = {}
  for root in roots:
    cbf[root] = []
    if ts_from_cbf:
      for filename in os.listdir(root):
        if os.path.splitext(filename)[1] != ".cbf": continue
        cbf[root].append(filename)
    else:
      for filename in os.listdir(root):
        if 'refined_experiments' not in os.path.splitext(filename)[0] or os.path.splitext(filename)[1] != ".json": continue
        explist=ExperimentListFactory.from_json_file(os.path.join(root,filename), check_format=False)
        for exp in explist:
          cbf[root].append(exp.imageset.get_image_identifier(0).split('/')[-1])
  # Now take intersection
  common_set = set(cbf[roots[0]])
  for ii in range(1, len(roots)):
    common_set = common_set.intersection(set(cbf[roots[ii]]))

  return list(common_set)

if __name__ == '__main__':
  if '--help' in sys.argv[1:] or '--h' in sys.argv[1:]:
    print (message)
  params = params_from_phil(sys.argv[1:])
  num_nodes = params.num_nodes #int(sys.argv[2])
  num_cores_per_node = params.num_cores_per_node
  num_cores = params.num_cores
  wall_time = params.wall_time
  if len(params.input_path) == 0:
    params.input_path=['.']
  roots = []
  for input_path in params.input_path:
    roots.append(os.path.join(input_path, 'out'))
  out_logfile = params.out_logfile
  steps_d = {}
  debug_mode=False
  write_out_timings=params.write_out_timings
  string_to_search_for = params.string_to_search_for
  show_plot = params.show_plot
  indexing_time_cutoff = params.indexing_time_cutoff
  common_set=None
  if len(roots) > 1:
    common_set = get_common_set(roots, ts_from_cbf=params.ts_from_cbf)
  for root in roots:
    run(params, root, common_set=common_set)
