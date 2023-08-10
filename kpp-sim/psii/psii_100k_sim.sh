#!/bin/bash -l
#SBATCH -N 128           # Number of nodes
#SBATCH -J psii_sim
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m2859_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular       # regular or special queue
#SBATCH -t 120
#SBATCH --gpus-per-node 4
#SBATCH -o %j.out
#SBATCH -e %j.err

export SCRATCH_FOLDER=$SCRATCH/psii/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export N_SIM=131072 # total number of images to simulate
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=4
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path


echo "
noise=True
psf=False
attenuation=True
context=kokkos_gpu
absorption=high_remote
oversample=2
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
  pdb.file=$MODULES/exafel_project/kpp-sim/psii/LS11_LS34_LQ39_LN84_LM51_all_OEC_1.92_1022_30.pdb
  length_um=50.0 # increase crystal path length
}
detector {
  tiles=multipanel
  reference=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
  offset_mm=100.0 # desired 1.7 somewhere between inscribed and circumscribed.
}
output {
  format=h5
  ground_truth=$SCRATCH_FOLDER/ground_truth.mtz
}
" > trial.phil

echo "jobstart $(date)";pwd
srun -n 4096 -c 4 libtbx.python "$MODULES"/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd
