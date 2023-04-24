#!/bin/bash -l
#SBATCH -N 8                # Number of nodes
#SBATCH -J stills_proc
#SBATCH -L SCRATCH          # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular    # regular queue
#SBATCH -t 00:30:00         # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

export SCRATCH_FOLDER=$SCRATCH/ferredoxin_sim/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

echo "jobstart $(date)";pwd
srun -n 256 -c 2 libtbx.python $MODULES/exafel_project/kpp-sim/compare_timing.py
echo "jobend $(date)";pwd
