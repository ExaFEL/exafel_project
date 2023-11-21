#!/bin/bash
SRUN="srun -c 2"
H5_SIM_PATH=$1
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export HOPPER_RESULTS=${H5_SIM_PATH}/stage1
export PANDA=${H5_SIM_PATH}/predict/preds_for_hopper.pkl
export MTZ_OLD=${H5_SIM_PATH}/merge/out/ly99sim_all.mtz
export MTZ=${H5_SIM_PATH}/merge/out/ly99sim_all.COMPLETE.mtz
diffBragg.completeF $MTZ_OLD $MTZ

export SCRATCH_FOLDER=${H5_SIM_PATH}/stage2
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=4

export DIFFBRAGG_USE_KOKKOS=1
export CCTBX_NO_UUID=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=64
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export MPI4PY_RC_RECV_MPROBE='False'
env > env.out

PHIL=stage2.phil

# copy over the hopper phil
cat $HOPPER_RESULTS/diff.phil > $PHIL 


echo "
method = 'L-BFGS-B'
debug_mode = False

sigmas {
  G = 1e-3
  Fhkl = 1
}

use_restraints = False

refiner {
  refine_Fcell = [1]
  refine_spot_scale = [1]
  max_calls = [2500]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 0.3
  num_devices = ${DEVICES_PER_NODE}
  adu_per_photon = 1
  res_ranges='1.6-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

logging {
  rank0_level = low normal *high
  logfiles = False  # True for memory troubleshooting but consumes 3 seconds of wall time
}
" >> $PHIL 

echo "jobstart $(date)";pwd
$SRUN simtbx.diffBragg.stage_two $PHIL \
    io.output_dir=. \
    pandas_table="${PANDA}" \
    refls_key=predictions_77perc \
    simulator.structure_factors.mtz_name="${MTZ}" \
    simulator.structure_factors.mtz_column="F(+),F(-)"
echo "jobend $(date)";pwd
