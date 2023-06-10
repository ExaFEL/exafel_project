#!/bin/bash -l
#SBATCH -N 1             # Number of nodes
#SBATCH -J ExaFEL_eA8    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:30:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA8"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

EXAFEL_D_BIN_COUNT=10
ExaFEL_eA6=/define/this/variable

echo "job start $(date)"; pwd
for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
  echo "
  hierarchy=2
  plot_max=0.3
  include_offset_dots=True
  dot_size=2
  include_scale_bar_in_pixels=1
  repredict_input_reflections=False
  unit_cell_histograms=False
  positional_displacements=False
  per_image_RMSDs_histogram=False
  residuals.exclude_outliers_from_refinement=False
  tag=combined
  residuals.mcd_filter.enable=True
  " > step_A8_bin"$EXAFEL_D_BIN".phil
  cctbx.xfel.detector_residuals \
    "$ExaFEL_eA6"/combined_stage1_bin"$EXAFEL_D_BIN".expt \
    "$ExaFEL_eA6"/combined_stage1_bin"$EXAFEL_D_BIN".refl \
    step_A8_bin"$EXAFEL_D_BIN".phil \
    > residuals_stage1_bin"$EXAFEL_D_BIN".log
done
echo "job end $(date)"; pwd