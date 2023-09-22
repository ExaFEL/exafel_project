#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eA1    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:60:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA1"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application

DIALS_JOB_OUT=/define/this/variable
STAGE1_JOB_OUT=/define/this/variable

echo -e "
dispatch.step_list = input balance substitute statistics_unitcell model_statistics annulus
input {
  path = $DIALS_JOB_OUT
  reflections_suffix = indexed.refl
  experiments_suffix = refined.expt
  persistent_refl_cols = shoebox
  persistent_refl_cols = bbox
  persistent_refl_cols = xyzcal.px
  persistent_refl_cols = xyzcal.mm
  persistent_refl_cols = xyzobs.px.value
  persistent_refl_cols = xyzobs.mm.value
  persistent_refl_cols = xyzobs.mm.variance
  persistent_refl_cols = delpsical.rad
  persistent_refl_cols = panel
  parallel_file_load.balance = global1 *global2 per_node
}
substitute.input = $STAGE1_JOB_OUT/hopper_stage_one/refls/rank*/*_refined_*.refl
substitute.apply = False
scaling.unit_cell=67.2  59.8  47.2  90.00  110.3  90.00
scaling.space_group=C 1 2/m 1
spread_roi.enable=True
spread_roi.strong=None
spread_roi.min_spots=5
exafel.scenario=1
merging.d_max=9999
merging.d_min=1.80
statistics.annulus.d_max=9999
statistics.annulus.d_min=1.80
output {
log_level = 0
  prefix = matching_DIALS
  output_dir = out/
  save_experiments_and_reflections = True
}
" > step_A1.phil

echo "job start $(date)"; pwd
srun -n 64 -c 4 cctbx.xfel.merge step_A1.phil
echo "job end $(date)"; pwd
