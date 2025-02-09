#!/bin/bash -l
#SBATCH -N 1              # Number of nodes
#SBATCH -J split
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular        # regular queue
#SBATCH -t 00:02:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
export JOB_ID_INDEX=$1

export SCRATCH_FOLDER=$SCRATCH/yb_lyso/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH/yb_lyso

echo "jobstart $(date)";pwd

srun -n 128 -c 2 diffBragg.make_input_file ${JOB_ID_INDEX} ${SLURM_JOB_ID}_integ_exp_ref.txt

echo "jobend $(date)";pwd
