## Scripts for running diffBragg stages 1 and 2 on Perlmutter
This directory houses scripts and phil files for processing the LZ08 dataset (cry1Aae mosquito toxin) collected at CXI on the Jungfrau 4M detector. The original cctbx.xfel processing of this dataset produced 77k images and a merged dataset described in the log file at `/pscratch/sd/c/cctbx/cxilz0820/common/results/cry1Ae_mark0_1.8_3/v021/cry1Ae_mark0_1.8_3_v021_main.log`. The goal with diffBragg is to start from the same set of integrated results and demonstrate local and global optimization.

diffBragg stage 1 executes local refinement of individual images. A successful result will be identifiable by plotting detector residuals and observing a change in the delta psi distribution on each panel. For this dataset we have not found the detector residuals (radial and transverse) to uniformly improve; some will get better and some will get worse, at best. However, this is in line with what we have observed for other datasets. 

### Stage 1

Stage 1 needs to be supplied a plain text file of a certain format describing where to find the data. This is given by the phil param `exp_ref_spec_file`, and each line in this file should be a path to an experiment json followed by a path to a matching integrated reflections pickle. (The order of these two matters.) An output directory should also be specified with the param outdir. The command to be run is `simtbx.diffBragg.hopper`.

Upon execution, stage 1 should generate a diff phil file as well as a plain-text file containing the command, working directory, and diff phil. It will produce six directories, each with subdirectories by rank, containing, respectively, experiment lists (.json), reflection tables (.refl), pandas tables (.pkl), image model information as paired numpy (.npy) and spectral (.lam) data, traces (.txt), and logs of the simulator state (.txt). These files must be findable by diffBragg stage 2, but should only need to be understood by the user in case of debugging.

### Stage 2

diffBragg stage 2 completes iterative global refinement of a set of structure factors against the entire set of integrated pixel intensities. (This excludes regions outside the shoeboxes.) In order to make use of these individual pixel data we also need to have measured spectra for each shot and have these represented in fine enough detail (small enough energy bins) that shots' energy histograms are measurably different; this is true for this dataset. 

Stage 2 is composed of a few steps. In practical terms, and for this dataset:

First, we need to generate simulated images matching each of the experimental images. As we update parameters, we update the simulated images and compare them with the real ones to determine whether there is an improvement in the agreement. This step is carried out by the command line program diffBragg.integrate which requires two sets of phil parameters, here `simulation.phil` and `sim_processing.phil`. `simulation.phil` describes parameters for simulated image generation, and `sim_processing.phil` describes parameters for processing the simulated images up through the integration step identically to how the experimental data were processed. The `sim_processing.phil` file therefore should match the parameters to stills_proccss. Many of the steps of stills_process are executed directly by diffBragg.integrate under the hood.

Important parameters in the image simulation step (`simulation.phil`) are:

    spectrum_from_imageset = True # Reads spectra. For datasets without per-shot spectra, you could turn this off.
    laue_mode = True              # This should be True if the above is True.
    qcut                          # qcut is an opaque but critical parameter to tune. Mistuned qcut looks like bad spotfinder results.
    resolution_range = [1,40]     # This should be reasonable for the experimental dataset (and within detector bounds).
    weak_fraction = 0.7           # Determines how many of the weak spots to include.
    threshold = 1e2               # Threshold is analogous to the same parameter in spotfinding.

The diffBragg.integrate command line program takes arguments `simulation.phil`, `sim_processing.phil`, input directory, and output directory. The input directory is where to look for the results of stage one processing. (The program will look for files in the organization and naming conventions used by stage one.) Additional command line arguments are as follows:

    --numdev 4                    # Specifies number of GPUs per node.
    --hopInputName pred           # Must match the column name of the predicted pixels in the pandas tables generated in stage one.
    --cmdlinePhil <kwargs>        # Any arguments passed here will override any arguments in the simulation.phil and sim_processing.phil files as applicable. 
                                  # Note, however, that some arguments must be supplied in the phil file and not with the --cmdlinePhil flag.

A successful run of diffbragg.integrate will produce a directory `reintegrated` and a log file as `reintegrated.exectution.txt` [sic]. Contents of `reintegrated` are grouped by rank.

Following this step, the command line program ens.hopper must be run twice with different inputs. The first time reads the input and generates "pre-imported" files that will take significantly less time to read with each cycle of global refinement. The second time carries out global refinement. These two runs are differentiated by the flag `--preImport` (pass on the first run). On the second run, you should supply the matching path that the first one generated. 

Parameters to ens.hopper describe the global parameters to refine. Here, these are encapsulated in `stage_two_test.phil`. A few are described below:

    prep_time = 60                # This time (in seconds) must be long enough for the "prep" steps to finish before all ranks start work.
                                  # This must be supplied in the phil file. (See below for further details.)
    spectrum_from_imageset = True # Should match pred.phil.
    use_restraints = False        # If False, the restraints are the data themselves. Otherwise we restrain to a starting model.

**More on `prep_time`:** If this parameter is passed as a `--cmdlinePhil` argument, we encounter two errors: first, `Sorry: Unknown command line parameter definition: prep_time = 60`, and second, a traceback in `hopper_ensemble.py`. If it is supplied in the phil file as expected, we will encounter the message `WARNING: unused phil: prep_time (input line 1)` on the first execution, and it will be correctly interpreted on the second execution.

*Update: prep_time should be deprecated in an incoming commit.*

On the first run, we must also specify `--outdir` and supply a directory name (e.g. "preimport") that we then match in the second run as a command line argument (without keywords and without flags). Any other arguments to the first run of ens.hopper are safely ignored, including command line arguments.

On the second run, we must be sure to pass `--refl ens.hopper.imported` (before the `--cmdlinePhil` flag, if present). We will also need a new `--outdir` specified here. This run will produce a directory `global` containing the structure factors at each saved iteration during global refinement, with the final result lacking an "iter" suffix, and the command line input saved as a text file. The final mtz is analogous to a merged mtz.

These three steps, diffBragg.integrate, ens.hopper (preimport) and ens.hopper (real execution), should each be run with a separate `srun` command inside the SLURM job.

### General note of caution
Many steps implicitly look for files in the working directory. Various things fail with misleading errors if things are not present or are not named as expected. I am working on removing this behavior, but the current scripts still reflect this state.

### Environment variables
Several of these are critical and unintuitive. Some are explained here:

    CUDA_LAUNCH_BLOCKING=1        # required for mysterious reasons
    NUMEXPR_MAX_THREADS=128       # correctly sets number of processors per node on Perlmutter
    SLURM_CPU_BIND=cores          # forces ranks onto separate cores. This is duplicated in the flag --cpu-bind=cores.
    OMP_PROC_BIND=spread          # distribute threads as evenly as possible over processors
    OMP_PLACES=threads            # pin threads to hardware threads
    HDF5_USE_FILE_LOCKING=FALSE   # allows many ranks to simultaneously read h5 files, which is critical for these data
    MPI4PY_RC_RECV_MPROBE='False' # required for mysterious reasons
    SIT_PSDM_DATA=/pscratch/sd/p/psdatmgr/data/pmscr 
                                  # this must be set to the above on Perlmutter or to /global/cfs/cdirs/lcls/psdm-sauter
                                  # if Perlmutter scratch is down *and* the data have been backed up to this alternative location.
                                  # This variable dictates where psana looks for the data associated with an experiment when reading a locator file.
    SIT_DATA=/global/common/software/lcls/psdm/data
                                  # another location for certain files needed by psana
    DIFFBRAGG_USE_CUDA=1          # this will eventually be replaced by DIFFBRAGG_USE_CUDA, but at present this covers all GPU acceleration.

### SLURM job submission

Necessary parameters are number of nodes (`-N`), allocation (`-A`, and ending in `_g` for GPU jobs), qos (`-q`), constraint (request GPUs with `-C GPU`), and number of GPUs (`--gpus`). If you don't request GPU resources but do try to use them, you'll get an error message about the device not being GPU capable. If you request GPU resources but don't specify the number of GPUs, or specify a number less than the number the srun commands try to use, you will get an "invalid device ordinal" error.

I recommend also providing a job name (`-J`) and walltime (`-t` in HH:MM:SS) that is only slightly longer than the time expected. This prevents situations where jobs hang and use up the entire maximum walltime allowed. 

At the beginning of the job script (before `srun`), you must set the environment variables *after* sourcing a build, as some of them are overwritten by the alcc-recipes `activate.sh` scripts.

`srun` commands should be supplied with additional flags as follows:

    -n 8                          # total number of GPUs available to the job
    -c 32                         # number of CPUs per task, which should be 2 * floor(64 / tasks_per_node) for GPUs. We have 4 tasks per node by default to match 4 GPUs per node.
