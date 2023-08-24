#!/bin/bash -l
#SBATCH -N 1
#SBATCH -J split
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 5
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS=$((SLURM_JOB_NUM_NODES*28))
export SRUN="srun -n $NTASKS --gpus-per-node=8 --cpus-per-gpu=7 --cpu-bind=cores"
echo "splitting on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export JOB_ID_INDEX=$1

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID

echo "jobstart $(date)";pwd

$SRUN diffBragg.make_input_file ${JOB_ID_INDEX} ${SLURM_JOB_ID}_integ_exp_ref.txt \
    --splitDir ${SLURM_JOB_ID}/splits

echo "jobend $(date)";pwd
