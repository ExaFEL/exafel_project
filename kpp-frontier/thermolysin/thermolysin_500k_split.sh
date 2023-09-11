#!/bin/bash -l
#SBATCH -N 32
#SBATCH -J split
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 20
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS=$((SLURM_JOB_NUM_NODES*56))
export SRUN="srun -n $NTASKS -c1 --cpu-bind=cores"
echo "splitting on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export JOB_ID_INDEX=$1

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
export MPI4PY_RC_RECV_MPROBE='False'

echo "jobstart $(date)";pwd

$SRUN diffBragg.make_input_file ${JOB_ID_INDEX} ${SLURM_JOB_ID}_integ_exp_ref.txt \
    --splitDir ${SLURM_JOB_ID}/splits

echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
