#!/bin/bash -l
#SBATCH -N 1              # Number of nodes
#SBATCH -J split
#SBATCH -A m2859          # allocation
#SBATCH -q debug        # regular queue
#SBATCH -C cpu
#SBATCH -t 00:20:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1

export SCRATCH_FOLDER=$SCRATCH/cry11ba/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH/cry11ba

echo "jobstart $(date)";pwd

srun -n 1 -c 4 diffBragg.make_input_file ${JOB_ID_INDEX} ${SLURM_JOB_ID}_integ_exp_ref.txt

echo "jobend $(date)";pwd
