#!/bin/bash -l
#SBATCH -N 2             # Number of nodes
#SBATCH -J ExaFEL_eA3    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:30:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA3"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

EXAFEL_D_MAX_VALUES="None 5.00 4.00 3.00 2.00"
EXAFEL_D_MIN_VALUES="5.00 4.00 3.00 2.00 1.50"
EXAFEL_D_MAX_ARRAY=("$EXAFEL_D_MAX_VALUES")
EXAFEL_D_MIN_ARRAY=("$EXAFEL_D_MIN_VALUES")
EXAFEL_D_BIN_COUNT=${#EXAFEL_D_MAX_ARRAY[@]}

echo "job start $(date)"; pwd
for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
  echo "
  dispatch.step_list = input balance statistics_unitcell model_statistics annulus
  input {
    path=$ExaFEL_eA1/out/
    experiments_suffix=.expt
    reflections_suffix=.refl
    parallel_file_load.method=uniform
    parallel_file_load.balance=global1
    keep_imagesets=True
    read_image_headers=False
    persistent_refl_cols=shoebox
    persistent_refl_cols=bbox
    persistent_refl_cols=xyzcal.px
    persistent_refl_cols=xyzcal.mm
    persistent_refl_cols=xyzobs.px.value
    persistent_refl_cols=xyzobs.mm.value
    persistent_refl_cols=xyzobs.mm.variance
    persistent_refl_cols=delpsical.rad
    persistent_refl_cols=panel
    parallel_file_load.method=uniform
  }
  scaling.model=$PDB_REFERENCE_DIRECTORY/reference.pdb
  scaling.unit_cell=67.2  59.8  47.2  90.00  110.3  90.00
  scaling.space_group=C121
  scaling.resolution_scalar=0.96
  merging.d_max=${EXAFEL_D_MAX_ARRAY[EXAFEL_D_BIN]}
  merging.d_min=${EXAFEL_D_MIN_ARRAY[EXAFEL_D_BIN]}
  statistics.annulus.d_max=${EXAFEL_D_MAX_ARRAY[EXAFEL_D_BIN]}
  statistics.annulus.d_min=${EXAFEL_D_MIN_ARRAY[EXAFEL_D_BIN]}
  spread_roi.enable=True
  spread_roi.strong=1.0
  output.log_level=0
  exafel.trusted_mask=None
  exafel.scenario=1
  output {
    prefix=strong_DIALS
    output_dir=out_bin${EXAFEL_D_BIN}/
    save_experiments_and_reflections=True
  }
  " > step_A3_bin"$EXAFEL_D_BIN".phil
  srun -n 128 -c 4 cctbx.xfel.merge step_A3_bin"$EXAFEL_D_BIN".phil
done
echo "job end $(date)"; pwd