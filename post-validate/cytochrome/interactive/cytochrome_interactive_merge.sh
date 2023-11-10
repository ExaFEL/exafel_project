SRUN="srun -c2"
H5_SIM_PATH=$1
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export SCRATCH_FOLDER=${H5_SIM_PATH}/merge
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export DIALS_OUTPUT=${H5_SIM_PATH}.index

export TRIAL=ly99sim
export OUT_DIR=${SCRATCH_FOLDER}
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
