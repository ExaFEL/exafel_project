#!/bin/bash
SRUN="srun -c2"
H5_SIM_PATH=$1
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export SCRATCH_FOLDER=${H5_SIM_PATH}/index
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export NUMEXPR_MAX_THREADS=16
export SLURM_CPU_BIND=cores
export OMP_PROC_BIND=spread
export OMP_PLACES=threads


export TRIAL=tdata
export OUT_DIR=.
export DIALS_OUTPUT=.
mkdir -p ${OUT_DIR}/${TRIAL}/out
mkdir -p ${OUT_DIR}/${TRIAL}/tmp
env > env.out

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
  filter.d_min=1.5
}
indexing {
  stills.refine_candidates_with_known_symmetry=True
  known_symmetry {
    space_group = 'P6522'
    unit_cell = 77.856 77.856 263.615 90 90 120
  }
}
integration {
  background.simple.outlier.plane.n_sigma=10
  #debug.output=True
  #debug.separate_files=False
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
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi

echo "dispatch.step_list=input tdata
input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
tdata.output_path=${TRIAL}_cells
output.output_dir=${OUT_DIR}/${TRIAL}/out
output.tmp_dir=${OUT_DIR}/${TRIAL}/tmp
output.do_timing=True
output.log_level=0
" > tdata.phil

echo "jobstart $(date)";pwd
echo "sleep for 10 seconds while slurm resets"
sleep 10
$SRUN cctbx.xfel.merge tdata.phil
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
