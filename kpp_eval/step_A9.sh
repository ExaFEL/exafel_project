#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eA9    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:30:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA9"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

echo "job start $(date)"; pwd
libtbx.python "$MODULES"/exafel_project/kpp_eval/summarise_offsets.py \
  residuals_log_glob="$ExaFEL_eA7"/residuals_DIALS_bin*.log \
  residuals_log_glob="$ExaFEL_eA8"/residuals_stage1_bin*.log
echo "job end $(date)"; pwd
