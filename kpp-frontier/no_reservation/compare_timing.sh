#!/bin/bash -l
#SBATCH -N 1024                # Number of nodes
#SBATCH -J read_timing
#SBATCH -A CHM137          # allocation
#SBATCH -p batch
#SBATCH -q debug           # regular queue
#SBATCH -t 00:20:00         # wall clock time limit
#SBATCH --mail-type=ALL
#SBATCH --mail-user=nksauter@lbl.gov
#SBATCH -o %j.out
#SBATCH -e %j.err

SRUN="srun -n 8192 -c 2"

export SCRATCH_FOLDER=$SCRATCH/read_timing/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER
export RESERVE_MODULES=${MODULES}

export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes3.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"

echo "jobstart $(date)";pwd
$SRUN libtbx.python $RESERVE_MODULES/exafel_project/kpp-frontier/no_reservation/compare_timing.py
echo "jobend $(date)";pwd
