#!/bin/bash -l
#SBATCH -N 32             # Number of nodes
#SBATCH -J split
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular        # regular queue
#SBATCH -t 00:15:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1

export SCRATCH_FOLDER=$SCRATCH/psii/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH/psii" || exit

echo "jobstart $(date)";pwd

srun -n 512 -c 16 diffBragg.make_input_file "$JOB_ID_INDEX" "${SLURM_JOB_ID}_integ_exp_ref.txt" --splitDir "${SLURM_JOB_ID}/splits"

echo "jobend $(date)";pwd
