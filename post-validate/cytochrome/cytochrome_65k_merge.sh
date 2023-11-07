#!/bin/bash -l
#SBATCH -N 16              # Number of nodes
#SBATCH -J cyto_merge      # job name
#SBATCH -L SCRATCH         # job requires SCRATCH files
#SBATCH -A m2859           # allocation
#SBATCH -C cpu
#SBATCH -q regular         # regular or special queue
#SBATCH -t 00:10:00        # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n 256 -c 16"

export SCRATCH_FOLDER=$SCRATCH/cytochrome/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export JOB_ID_INDEX=$1
export DIALS_OUTPUT=$SCRATCH/cytochrome/$JOB_ID_INDEX

export TRIAL=ly99sim
export OUT_DIR=$SCRATCH/cytochrome/$SLURM_JOB_ID
export MPI4PY_RC_RECV_MPROBE='False'

mkdir -p "${OUT_DIR}/${TRIAL}/out"
mkdir -p "${OUT_DIR}/${TRIAL}/tmp"
env > env.out

echo "input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
filter.algorithm=unit_cell
filter.unit_cell.algorithm=cluster
filter.unit_cell.cluster.covariance.file=${MODULES}/exafel_project/kpp-frontier/cytochrome/covariance_tdata_cells.pickle
filter.unit_cell.cluster.covariance.component=0
filter.unit_cell.cluster.covariance.mahalanobis=5.0
filter.outlier.min_corr=-1.0
select.algorithm=significance_filter
select.significance_filter.sigma=0.1
scaling.model=${MODULES}/exafel_project/kpp-frontier/cytochrome/5wp2.pdb
scaling.resolution_scalar=0.993420862158964
postrefinement.enable=True
postrefinement.algorithm=rs
merging.d_min=1.5
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
