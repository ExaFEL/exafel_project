#!/bin/bash -l
#SBATCH -N 4              # Number of nodes
#SBATCH -J split
#SBATCH -A CHM137          # allocation
#SBATCH -p batch        # regular queue
#SBATCH -t 00:20:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1

export SCRATCH_FOLDER=$SCRATCH/psii/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH/psii" || exit

echo "jobstart $(date)";pwd

srun -n 64 -c 2 diffBragg.make_input_file "$JOB_ID_INDEX" "${SLURM_JOB_ID}_integ_exp_ref.txt"

echo "jobend $(date)";pwd
