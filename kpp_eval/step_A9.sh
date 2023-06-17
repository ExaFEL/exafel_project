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

ExaFEL_eA7=/define/this/variable
ExaFEL_eA8=/define/this/variable

EXAFEL_D_MAX_VALUES="None 5.00 4.00 3.00 2.00"
EXAFEL_D_MIN_VALUES="5.00 4.00 3.00 2.00 1.50"
EXAFEL_D_MAX_ARRAY=($EXAFEL_D_MAX_VALUES)
EXAFEL_D_MIN_ARRAY=($EXAFEL_D_MIN_VALUES)
EXAFEL_D_BIN_COUNT=${#EXAFEL_D_MAX_ARRAY[@]}

EXAFEL_PHIL_A9_TEXT="processing {"
for EXAFEL_D_BIN in $(seq 1 $EXAFEL_D_BIN_COUNT); do
  EXAFEL_PHIL_A9_TEXT="${EXAFEL_PHIL_A9_TEXT}\n  bin {
    path = $ExaFEL_eA7/residuals_DIALS_bin$EXAFEL_D_BIN.log
    d_max = ${EXAFEL_D_MAX_ARRAY[$EXAFEL_D_BIN-1]}
    d_min = ${EXAFEL_D_MIN_ARRAY[$EXAFEL_D_BIN-1]}
  }"
done
EXAFEL_PHIL_A9_TEXT="${EXAFEL_PHIL_A9_TEXT}\n}\nprocessing {"
for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
  EXAFEL_PHIL_A9_TEXT="${EXAFEL_PHIL_A9_TEXT}\n  bin {
    path = $ExaFEL_eA8/residuals_stage1_bin$EXAFEL_D_BIN.log
    d_max = ${EXAFEL_D_MAX_ARRAY[$EXAFEL_D_BIN-1]}
    d_min = ${EXAFEL_D_MIN_ARRAY[$EXAFEL_D_BIN-1]}
  }"
done
EXAFEL_PHIL_A9_TEXT="${EXAFEL_PHIL_A9_TEXT}\n}"
echo -e EXAFEL_PHIL_A9_TEXT > step_A9.phil

echo "job start $(date)"; pwd
libtbx.python "$MODULES"/exafel_project/kpp_eval/summarise_offsets.py step_A9.phil
echo "job end $(date)"; pwd
