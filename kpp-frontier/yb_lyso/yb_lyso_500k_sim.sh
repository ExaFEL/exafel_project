#!/bin/bash -l
#SBATCH -N 64            # Number of nodes
#SBATCH -J high_remote_lysozyme_sim
#SBATCH -A CHM137       # allocation
#SBATCH -p batch       # regular or special queue
#SBATCH -t 120
#SBATCH --mail-type=ALL
#SBATCH --mail-user=fwittwer@lbl.gov
#SBATCH -o %j.out
#SBATCH -e %j.err

export SCRATCH_FOLDER=$SCRATCH/yb_lyso/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export LENGTH=${1}
export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export N_SIM=524288 # total number of images to simulate
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=4
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=32
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

# determine oversample with simple difference script IN PROCESS
# check that both sim and expt have gain==1
# define ncells as 10x10x10 ???  not sure how ncells is now gotten
# store constant background for all images
# xtal size mm 0.00015
# mos domains 50 (my default 25)
# mos spread deg 0.01 (my default 0.05)
# --masterscale 1150 --sad --bs7real --masterscalejitter 115

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
  # Perlmutter OK-download in job from PDB
  # structure=pdb
  # pdb.code=4bs7 # Yb lysozyme, Celia Sauter(no relation), 1.7 Angstrom
  # Frontier OK-take PDB file from github
  structure=pdb
  pdb.code=None
  pdb.source=file
  pdb.file=${MODULES}/cxid9114/sim/4bs7.pdb
  length_um=${LENGTH} # X-ray path through the crystal in microns
}
detector {
  tiles=multipanel
  reference=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
  offset_mm=80.0 # desired 1.7 somewhere between inscribed and circumscribed.
}
output {
  format=h5
  ground_truth=${SCRATCH_FOLDER}/ground_truth.mtz
}
" > trial.phil

echo "jobstart $(date)";pwd
srun -n 2048 -c 1 libtbx.python $MODULES/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd
