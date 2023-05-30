#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_1_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m2859_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 01:30:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH -o %j.out
#SBATCH -e %j.err

export SCRATCH_FOLDER=$SCRATCH/ferredoxin_sim/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=1
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


echo "jobstart $(date)";pwd

srun -n 256 -G 128 -c 16 diffBragg.integrate $MODULES/exafel_project/kpp-sim/integrate_stage1_kokkos.phil $MODULES/exafel_project/kpp-sim/index.phil $SCRATCH/ferredoxin_sim/9689612/hopper_stage_one out --numdev 1

echo "jobend $(date)";pwd