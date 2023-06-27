#!/bin/bash -l
#SBATCH -N 32             # Number of nodes
#SBATCH -J high_remote_ferredoxin_sim
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -C gpu
#SBATCH -q regular # regular or special queue
#SBATCH --gpus-per-node 4
#SBATCH -o %j.out
#SBATCH -e %j.err

. $MODULES/exafel_project/kpp-sim/sim_ferredoxin_high_remote_setup.sh $1

echo "jobstart $(date)";pwd
srun -n 1024 -c 4 libtbx.python $MODULES/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd
