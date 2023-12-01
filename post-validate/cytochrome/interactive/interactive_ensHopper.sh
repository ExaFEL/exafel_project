#!/bin/bash
SRUN="srun -c 2"
D_MIN=$1
H5_SIM_PATH=$2
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export HOPPER_RESULTS=${H5_SIM_PATH}/stage1
export PANDA=${H5_SIM_PATH}/predict/preds_for_hopper.pkl
export MTZ_OLD=${H5_SIM_PATH}/merge/out/ly99sim_all.mtz
export MTZ=${H5_SIM_PATH}/merge/out/ly99sim_all.COMPLETE.mtz
diffBragg.completeF $MTZ_OLD $MTZ

export SCRATCH_FOLDER=${H5_SIM_PATH}/ensHopper
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
debug_mode = False

sigmas {
  G = 0.001
  Fhkl = 1
}

types.G = positive

use_geometric_mean_Fhkl=True
betas.Fhkl = 1e3

fix {
  Nabc = True
  RotXYZ = True
  ucell = True
  detz_shift = True
  eta_abc = True
  G = False
  Fhkl = False
}

refiner.res_ranges='$D_MIN-999'

logging {
  rank0_level = low normal *high
  logfiles = True  # True for memory troubleshooting but consumes 3 seconds of wall time
}
" >> $PHIL 

echo "jobstart $(date)";pwd
$SRUN ens.hopper $PANDA $PHIL --outdir . \
  --cmdlinePhil \
  simulator.structure_factors.mtz_name="${MTZ}" \
  simulator.structure_factors.mtz_column="F(+),F(-)" \
  --refl predictions_77perc \
  --saveFreq 10

echo "jobend $(date)";pwd

