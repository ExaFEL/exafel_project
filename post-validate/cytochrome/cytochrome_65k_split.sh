#!/bin/bash -l
#SBATCH -N 1              # Number of nodes
#SBATCH -J cyto_split
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular        # regular queue
#SBATCH -t 00:05:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n 128 -c 2"

export JOB_ID_INDEX=$1

echo "jobstart $(date)";pwd
$SRUN diffBragg.make_input_file "$JOB_ID_INDEX" "${SLURM_JOB_ID}_integ_exp_ref.txt"
echo "jobend $(date)";pwd
