#!/bin/bash -l
#SBATCH -N 256
#SBATCH -J merge
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 60
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS_PER_NODE=56
export NTASKS=$((SLURM_JOB_NUM_NODES * NTASKS_PER_NODE))
export SRUN="srun -N$SLURM_JOB_NUM_NODES -n$NTASKS -c1 --cpu-bind=cores"
echo "merging on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export JOB_ID_INDEX=$1

export DIALS_OUTPUT=$SCRATCH/thermolysin/$JOB_ID_INDEX
export TRIAL=ly99sim
export OUT_DIR=$SCRATCH/thermolysin/$SLURM_JOB_ID
export MPI4PY_RC_RECV_MPROBE='False'

mkdir -p ${OUT_DIR}/${TRIAL}/out
mkdir -p ${OUT_DIR}/${TRIAL}/tmp
echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
env > env.out

echo "input.path=${DIALS_OUTPUT}
dispatch.step_list=input balance model_scaling modify filter scale postrefine statistics_unitcell statistics_beam model_statistics statistics_resolution group errors_merge merge statistics_intensity_cxi
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
filter.algorithm=unit_cell
filter.unit_cell.algorithm=cluster
filter.unit_cell.cluster.covariance.file=${MODULES}/exafel_project/kpp-sim/thermolysin/covariance_tdata_cells_cropped.pickle
filter.unit_cell.cluster.covariance.component=0
filter.unit_cell.cluster.covariance.mahalanobis=5.0
filter.outlier.min_corr=-1.0
select.algorithm=significance_filter
select.significance_filter.sigma=0.1
scaling.model=${MODULES}/exafel_project/kpp-sim/thermolysin/4tnl.pdb
scaling.resolution_scalar=0.993420862158964
postrefinement.enable=True
postrefinement.algorithm=rs
merging.d_min=1.7
merging.merge_anomalous=False
merging.set_average_unit_cell=True
merging.error.model=ev11
#merging.error.model=errors_from_sample_residuals
statistics.n_bins=20
statistics.report_ML=True
output.prefix=${TRIAL}
output.output_dir=${OUT_DIR}/out
output.tmp_dir=${OUT_DIR}/tmp
output.do_timing=True
output.log_level=0
output.save_experiments_and_reflections=True
parallel.a2a=1
" > merge.phil

echo "jobstart $(date)";pwd
$SRUN cctbx.xfel.merge merge.phil
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
