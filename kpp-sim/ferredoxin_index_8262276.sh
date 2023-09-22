#!/bin/bash -l
#SBATCH -N 8                # Number of nodes
#SBATCH -J stills_proc
#SBATCH -L SCRATCH          # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular    # regular queue
#SBATCH -t 01:30:00         # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

export H5_SIM_PATH=$SCRATCH/ferredoxin_sim/7200040

export SCRATCH_FOLDER=$SCRATCH/ferredoxin_sim/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

echo "
output {
  composite_output = False
  logging_dir=. # demangle by rank
}
dispatch {
  index=True
  refine=True
  integrate=True
}
mp.method = mpi
spotfinder {
  lookup {
    #mask = "/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask"
  }
  threshold {
    dispersion {
      gain = 1.0 # for nanoBragg sim
      sigma_background=2
      sigma_strong=2
      global_threshold=10
      kernel_size=6 6
    }
  }
  filter.min_spot_size=3
  filter.d_min=1.9
}
indexing {
  stills.refine_candidates_with_known_symmetry=True
  known_symmetry {
    space_group = "C2"
    unit_cell = 67.2 59.8 47.2 90 113.2 90
  }
}
integration {
  background.simple.outlier.plane.n_sigma=10
  debug.output=True
  debug.separate_files=False
  lookup {
    #mask = "/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask"
  }
  summation {
    detector_gain = 1.0 # for nanoBragg sim
  }
}
profile.gaussian_rs.centroid_definition=com
">trial.phil

echo "jobstart $(date)";pwd
srun -n 256 -c 2 dials.stills_process trial.phil input.glob=$H5_SIM_PATH/image_rank_*.h5
echo "jobend $(date)";pwd
export TRIAL=tdata
export OUT_DIR=.
export DIALS_OUTPUT=.


echo "dispatch.step_list=input tdata
input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
tdata.output_path=${TRIAL}_cells
output.prefix=${TRIAL}
output.output_dir=${OUT_DIR}/${TRIAL}/out
output.tmp_dir=${OUT_DIR}/${TRIAL}/tmp
output.do_timing=True
output.log_level=0
" > tdata.phil

mkdir -p ${OUT_DIR}/${TRIAL}/out
mkdir -p ${OUT_DIR}/${TRIAL}/tmp

echo "jobstart $(date)";pwd
srun -n 256 -c 2 cctbx.xfel.merge tdata.phil
echo "jobend $(date)";pwd
