#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eval
#SBATCH -A m2859         # allocation
#SBATCH -C cpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:10:00      # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="interactive"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

echo "
input {
  mtz=path/to/dials.mtz
  mtz=path/to/diffBragg.mtz
  pdb=path/to/reference.pdb
}
output {
  prefix=kpp_eval
}
" > evaluate.phil
cp ../evaluate.sh .

echo "jobstart $(date)"; pwd
libtbx.python $MODULES/exafel_project/kpp-eval/evaluate.py evaluate.phil
echo "jobend $(date)"; pwd
