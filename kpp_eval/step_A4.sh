#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eA4    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:60:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA4"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

ExaFEL_eA2=/define/this/variable

# WARNING: sub-sample input based on path – otherwise output too much (~50GB)

echo "
hierarchy_level=2
dot_size=2
repredict_input_reflections=False
plots.unit_cell_histograms=False
plots.positional_displacements=False
plots.per_image_RMSDs_histogram=False
residuals.exclude_outliers_from_refinement=False
tag=combined_stage1
residuals.mcd_filter.enable=True
save_png=True
" > step_A4.phil

echo "job end $(date)"; pwd
dials.combine_experiments \
  "$ExaFEL_eA2"/out/matching_stage1*0.expt \
  "$ExaFEL_eA2"/out/matching_stage1*0.refl \
  output.experiments_filename=combined_stage1.expt \
  output.reflections_filename=combined_stage1.refl \
  > combined_stage1.log
cctbx.xfel.detector_residuals combined_stage1.expt combined_stage1.refl \
  step_A4.phil > residuals_stage1.log
echo "job end $(date)"; pwd
