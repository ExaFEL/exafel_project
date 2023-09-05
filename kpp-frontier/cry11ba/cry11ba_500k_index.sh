#!/bin/bash -l
#SBATCH -N 64                # Number of nodes
#SBATCH -J stills_proc
#SBATCH -A CHM137          # allocation
#SBATCH -p batch    # regular queue
#SBATCH -t 01:00:00
#SBATCH --mail-type=ALL
#SBATCH --mail-user=nksauter@lbl.gov
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n1024 -c2"

export JOB_ID_SIM=$1

export NUMEXPR_MAX_THREADS=32
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

export H5_SIM_PATH=$SCRATCH/cry11ba/$JOB_ID_SIM

export SCRATCH_FOLDER=$SCRATCH/cry11ba/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

echo "
output {
  composite_output = True
  integration_pickle=None
  logging_dir=. # demangle by rank
  logging_option=*suppressed disabled normal
}
dispatch {
  index=True
  refine=True
  integrate=True
}
mp.method = mpi
spotfinder {
  lookup {
    #mask = '/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask'
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
  filter.d_min=2.4
}
indexing {
  stills.refine_candidates_with_known_symmetry=True
  known_symmetry {
    space_group = 'P21212'
    unit_cell = 168.245 158.528 57.534 90 90 90
  }
}
integration {
  background.simple.outlier.plane.n_sigma=10
  #debug.output=True
  #debug.separate_files=False
  lookup {
    #mask = '/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask'
  }
  summation {
    detector_gain = 1.0 # for nanoBragg sim
  }
}
profile.gaussian_rs.centroid_definition=com

indexing.stills.refine_all_candidates=False
refinement.reflections.outlier.algorithm=None
dispatch.refine=True
indexing.stills.nv_reject_outliers=False
">index.phil

echo "jobstart $(date)";pwd
$SRUN dials.stills_process index.phil input.glob=$H5_SIM_PATH/image_rank_*.h5
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
$SRUN cctbx.xfel.merge tdata.phil
echo "jobend $(date)";pwd
