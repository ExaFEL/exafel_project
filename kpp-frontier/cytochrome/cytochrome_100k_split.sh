#!/bin/bash -l
#SBATCH -N 4               # Number of nodes
#SBATCH -J split           # job name
#SBATCH -A CHM137          # allocation
#SBATCH -p batch           # regular queue
#SBATCH -t 00:05:00        # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n 224 -c 1"

export JOB_ID_INDEX=$1

cd "$SCRATCH"/cytochrome || exit

echo "jobstart $(date)";pwd
$SRUN diffBragg.make_input_file "$JOB_ID_INDEX" "$SLURM_JOB_ID"_integ_exp_ref.txt
echo "jobend $(date)";pwd
