#!/bin/bash -l
#SBATCH -N 16              # Number of nodes
#SBATCH -J split
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular        # regular queue
#SBATCH -t 00:05:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1

export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH/thermolysin

echo "jobstart $(date)";pwd

srun -n 512 -c 8 diffBragg.make_input_file ${JOB_ID_INDEX} ${SLURM_JOB_ID}_integ_exp_ref.txt --splitDir ${SLURM_JOB_ID}/splits

echo "jobend $(date)";pwd
