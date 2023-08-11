#!/bin/bash -l
#SBATCH -N 1              # Number of nodes
#SBATCH -J cluster
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular          # regular queue
#SBATCH -t 00:10:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1
export SCRIPTS_FOLDER="$PWD"
export INDEX_FOLDER="$SCRATCH/psii/$JOB_ID_INDEX"
cd "$INDEX_FOLDER" || exit

echo "jobstart $(date)";pwd
uc_metrics.dbscan file_name=tdata_cells.tdata space_group=Pmmm feature_vector=a,b,c write_covariance=True plot.outliers=True eps=0.5
cd "$SCRIPTS_FOLDER" || exit
echo "jobend $(date)";pwd
