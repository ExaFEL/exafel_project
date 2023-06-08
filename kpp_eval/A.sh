#!/bin/bash -l
#SBATCH -N 10            # Number of nodes
#SBATCH -J ExaFEL_evalA
#SBATCH -A m2859         # allocation
#SBATCH -C cpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:30:00      # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="interactive"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

EXAFEL_D_MAX_VALUES="None 5.00 4.00 3.00 2.00"
EXAFEL_D_MIN_VALUES="5.00 4.00 3.00 2.00 1.50"
EXAFEL_D_MAX_ARRAY=("$EXAFEL_D_MAX_VALUES")
EXAFEL_D_MIN_ARRAY=("$EXAFEL_D_MIN_VALUES")
EXAFEL_D_BIN_COUNT=${#EXAFEL_D_MAX_ARRAY[@]}

for EXAFEL_RUN in DIALS diffBragg; do
  if [ $EXAFEL_RUN = "DIALS" ]; then
    EXAFEL_SUBSTITUTE_APPLY="False"
  else
    EXAFEL_SUBSTITUTE_APPLY="True"
  fi
  echo -p "
  dispatch.step_list = input balance substitute
  input {
    path = $EXAFEL_DIRECTORY/stage1/out
    reflections_suffix = refined.refl
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
  substitute {
    input = $EXAFEL_DIRECTORY/stage1/out/*integrated.refl
    apply = $EXAFEL_SUBSTITUTE_APPLY
  }
  output {
    prefix = substitute_$EXAFEL_RUN
    output_dir = out/$EXAFEL_RUN
    log_level = 0
    save_experiments_and_reflections = True
  }
  " > evaluate_offset_${EXAFEL_RUN}.phil

  for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
    echo -p "
    input {
      path=./out/$EXAFEL_RUN
      experiments_suffix=.expt
      reflections_suffix=.refl
      parallel_file_load.method=uniform
      parallel_file_load.balance=global1
    }
    dispatch.step_list = input balance statistics_unitcell model_statistics annulus
    input.keep_imagesets=True
    input.read_image_headers=False
    input.persistent_refl_cols=shoebox
    input.persistent_refl_cols=bbox
    input.persistent_refl_cols=xyzcal.px
    input.persistent_refl_cols=xyzcal.mm
    input.persistent_refl_cols=xyzobs.px.value
    input.persistent_refl_cols=xyzobs.mm.value
    input.persistent_refl_cols=xyzobs.mm.variance
    input.persistent_refl_cols=delpsical.rad
    input.persistent_refl_cols=panel
    input.parallel_file_load.method=uniform
    scaling.model=$EXAFEL_DIRECTORY/reference.pdb
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
    output.output_dir=out/${EXAFEL_RUN}_bin${EXAFEL_D_BIN}
    output.save_experiments_and_reflections=True
    " > evaluate_offset_"${EXAFEL_RUN}"_bin"${EXAFEL_D_BIN}".phil

    echo -p "
    output.experiments_filename=combined_${EXAFEL_RUN}${EXAFEL_D_BIN}.expt
    output.reflections_filename=combined_${EXAFEL_RUN}${EXAFEL_D_BIN}.refl
    " > evaluate_offset_"${EXAFEL_RUN}"_combine"${EXAFEL_D_BIN}".phil

    echo -p "
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
    " > evaluate_offset_"${EXAFEL_RUN}"_residuals"${EXAFEL_D_BIN}".phil
  done
done

cp ../evaluate_offset.sh .
cd $RESULTS_DIRECTORY || exit

echo "JOB START: $(date)"; pwd
srun -N 5 -n 80 -c 16 cctbx.xfel.merge evaluate_offset_DIALS.phil &
srun -N 5 -n 80 -c 16 cctbx.xfel.merge evaluate_offset_diffBragg.phil &
wait
for EXAFEL_RUN in DIALS diffBragg; do
  for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
    srun -N 1 -n 64 -c 4 cctbx.xfel.merge evaluate_offset_"${EXAFEL_RUN}"_bin"${EXAFEL_D_BIN}".phil &
  done
  wait
done
for EXAFEL_RUN in DIALS diffBragg; do
  for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
    (cd ./out/"${EXAFEL_RUN}"_bin"${EXAFEL_D_BIN}" &&
    srun -N 1 dials.combine_experiments ./*.expt ./*.refl \
    ../../evaluate_offset_"${EXAFEL_RUN}"_combine"${EXAFEL_D_BIN}".phil \
    > combine_experiments.log) &
  done
  wait
done
for EXAFEL_RUN in DIALS diffBragg; do
  for EXAFEL_D_BIN in $(seq 1 "$EXAFEL_D_BIN_COUNT"); do
    (cd ./out/"${EXAFEL_RUN}"_bin"${EXAFEL_D_BIN}" &&
    srun -N 1 cctbx.xfel.detector_residuals \
    ../../evaluate_offset_"${EXAFEL_RUN}"_residuals"${EXAFEL_D_BIN}".phil \
    > detector_residuals.log) &
  done
  wait
done
echo "jobend $(date)"; pwd
