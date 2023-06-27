#!/bin/bash -l
#SBATCH -N 32             # Number of nodes
#SBATCH -J high_remote_ferredoxin_sim
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -C gpu
#SBATCH -q regular # regular or special queue
#SBATCH --gpus-per-node 4
#SBATCH -o %j.out
#SBATCH -e %j.err

. sim_ferredoxim_high_remote_setup.sh $1

echo "jobstart $(date)";pwd
srun -n 1024 -c 4 sim_ferredoxin_high_remote.sh
echo "jobend $(date)";pwd
