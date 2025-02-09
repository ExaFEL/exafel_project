#!/bin/bash -l
#SBATCH -N 80            # Number of nodes
#SBATCH -J a13-241test   # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m3890_g       # allocation
#SBATCH -C gpu
#SBATCH -q early_science # regular or special queue
#SBATCH -t 00:15:00      # wall clock time limit
#SBATCH --gpus-per-node=4
#SBATCH -o job%j.out
#SBATCH -e job%j.err

export WORK=$PSCRATCH/nesap/adse13-241/work/
export MODULES=$PSCRATCH/xfel2/alcc-recipes/cctbx/modules
cd $WORK

export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export N_SIM=100000 # total number of images to simulate
export ADD_BACKGROUND_ALGORITHM=cuda # cuda or jh or sort_stable
export DEVICES_PER_NODE=4
export MOS_DOM=25

export CUDA_LAUNCH_BLOCKING=1

mkdir $SLURM_JOB_ID; cd $SLURM_JOB_ID
echo "jobstart $(date)";pwd
srun -n 640 -c 2 libtbx.python $MODULES/LS49/adse13_196/revapi/step5_batch.py context=kokkos_gpu
echo "jobend $(date)";pwd

