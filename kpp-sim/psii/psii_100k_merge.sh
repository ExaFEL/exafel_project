#!/bin/bash -l
#SBATCH -N 32              # Number of nodes
#SBATCH -J merge
#SBATCH -L SCRATCH        # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular        # regular queue
#SBATCH -t 00:45:00       # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INDEX=$1
export DIALS_OUTPUT=${SCRATCH}/psii/$JOB_ID_INDEX

export SCRATCH_FOLDER=$SCRATCH/psii/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export TRIAL=ly99sim
export OUT_DIR=${PWD}

echo "input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
filter.algorithm=unit_cell
filter.unit_cell.algorithm=cluster
filter.unit_cell.cluster.covariance.file=${MODULES}/exafel_project/kpp-sim/psii/covariance_tdata_cells.pickle
filter.unit_cell.cluster.covariance.component=0
filter.unit_cell.cluster.covariance.mahalanobis=5.0
filter.outlier.min_corr=-1.0
select.algorithm=significance_filter
select.significance_filter.sigma=-0.5
scaling.model=${MODULES}/exafel_project/kpp-sim/psii/LS11_LS34_LQ39_LN84_LM51_all_OEC_1.92_1022_30.pdb
scaling.resolution_scalar=0.993420862158964
postrefinement.enable=True
postrefinement.algorithm=rs
merging.d_min=1.9
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

mkdir -p "${OUT_DIR}/${TRIAL}/out"
mkdir -p "${OUT_DIR}/${TRIAL}/tmp"

echo "jobstart $(date)";pwd
srun -n 512 -c 16 cctbx.xfel.merge merge.phil
echo "jobend $(date)";pwd
