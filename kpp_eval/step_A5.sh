#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eA5    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:60:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA5"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

EXAFEL_D_BIN_COUNT=5
ExaFEL_eA3=/define/this/variable

echo "job end $(date)"; pwd
for EXAFEL_D_BIN in $(seq 1 $EXAFEL_D_BIN_COUNT); do
  dials.combine_experiments \
    "$ExaFEL_eA3"/out_bin"$EXAFEL_D_BIN"/strong_DIALS*.expt \
    "$ExaFEL_eA3"/out_bin"$EXAFEL_D_BIN"/strong_DIALS*.refl \
    output.experiments_filename=combined_DIALS_bin"$EXAFEL_D_BIN".expt \
    output.reflections_filename=combined_DIALS_bin"$EXAFEL_D_BIN".refl \
    > combined_DIALS_bin"$EXAFEL_D_BIN".log
done
echo "job end $(date)"; pwd
