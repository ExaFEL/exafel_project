#!/bin/bash
SRUN="srun -c2"
export LENGTH=$1 # micron length of crystal
export N_SIM=$2 # total number of images to simulate
export SCRATCH_FOLDER=$3
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=4  # THIS IS USED in LY99_batch.py
export MOS_DOM=26

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export MPI4PY_RC_RECV_MPROBE='False'
env > env.out

echo "
noise=True
psf=False
attenuation=True
context=kokkos_gpu
absorption=high_remote
oversample=1
beam {
  mean_energy=9500.
}
spectrum {
  nchannels=100
  channel_width=1.0
}
crystal {
  structure=pdb
  pdb.code=None
  pdb.source=file
  pdb.file=${MODULES}/exafel_project/kpp-frontier/cytochrome/5wp2.pdb
  length_um=${LENGTH}
}
detector {
  tiles=multipanel
  reference=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
  offset_mm=30.0  # desired 1.5 somewhere between inscribed and circumscribed.
}
output {
  format=h5
  ground_truth=${SCRATCH_FOLDER}/ground_truth.mtz
}
" > trial.phil

echo "jobstart $(date)";pwd
$SRUN libtbx.python $MODULES/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd
#if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
