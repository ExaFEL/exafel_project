#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A lcls_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:36:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH --gpus 128
#SBATCH -o %j.out
#SBATCH -e %j.err

export PERL_NDEV=1  # number GPU per node
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_CUDA=1

echo "jobstart $(date)";pwd

srun -n 256 -G 128 -c 2 hopper $MODULES/exafel_project/kpp-sim/hopper_stage1.phil exp_ref_spec

echo "jobend $(date)";pwd