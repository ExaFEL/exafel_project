#!/bin/bash -l
#SBATCH -N 32              # Number of nodes
#SBATCH -J merge
#SBATCH -A CHM137          # allocation
#SBATCH -p batch        # regular queue
#SBATCH -t 01:00:00       # wall clock time limit
#SBATCH --mail-type=ALL
#SBATCH --mail-user=nksauter@lbl.gov
#SBATCH -o %j.out
#SBATCH -e %j.err

export NTASKS=$((SLURM_JOB_NUM_NODES*56))
export SRUN="srun -n $NTASKS --gpus-per-node=8 --cpus-per-gpu=7 --cpu-bind=cores"
echo "merging on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export JOB_ID_SIM=$1
export JOB_ID_INDEX=$2
export DIALS_OUTPUT=${SCRATCH}/cry11ba/$JOB_ID_INDEX

export SCRATCH_FOLDER=$SCRATCH/cry11ba/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export TRIAL=cry11ba_500k
export OUT_DIR=${PWD}

echo "
dispatch.step_list=input balance model_scaling modify filter scale postrefine statistics_unitcell statistics_beam model_statistics statistics_resolution group errors_merge merge statistics_intensity_cxi
input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
filter.algorithm=unit_cell
filter.unit_cell.algorithm=cluster
filter.unit_cell.cluster.covariance.file=${MODULES}/exafel_project/kpp-frontier/cry11ba/covariance_tdata_cells_20000.pickle
filter.unit_cell.cluster.covariance.component=0
filter.unit_cell.cluster.covariance.mahalanobis=2.0
filter.outlier.min_corr=-1.0
select.algorithm=significance_filter
select.significance_filter.sigma=0.1
scaling.model=${MODULES}/exafel_project/kpp-sim/cry11ba/7qyd.pdb
scaling.resolution_scalar=0.993420862158964
postrefinement.enable=True
postrefinement.algorithm=rs
merging.d_min=2.3
merging.merge_anomalous=False
merging.set_average_unit_cell=True
merging.error.model=ev11
#merging.error.model=errors_from_sample_residuals
statistics.n_bins=20
statistics.report_ML=True
statistics.cciso.mtz_file=${SCRATCH}/cry11ba/${JOB_ID_SIM}/ground_truth.mtz
statistics.cciso.mtz_column_F=F
output.prefix=${TRIAL}
output.output_dir=${OUT_DIR}/out
output.tmp_dir=${OUT_DIR}/tmp
output.do_timing=True
output.log_level=0
output.save_experiments_and_reflections=True
parallel.a2a=1
" > merge.phil

mkdir -p ${OUT_DIR}/${TRIAL}/out
mkdir -p ${OUT_DIR}/${TRIAL}/tmp

echo "jobstart $(date)";pwd
$SRUN cctbx.xfel.merge merge.phil
echo "jobend $(date)";pwd
