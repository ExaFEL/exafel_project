export SCRATCH_FOLDER=$SCRATCH/ferredoxin_sim/small_example
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export N_SIM=3 # total number of images to simulate
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=1
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_CUDA=1
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
beam {
  mean_wavelength=7120.
}
output {
  format=h5
}
" > trial.phil

echo "jobstart $(date)";pwd
libtbx.python $MODULES/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd