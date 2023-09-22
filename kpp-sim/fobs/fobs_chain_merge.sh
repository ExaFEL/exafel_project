#!/bin/bash -l
#SBATCH -N 2               # Number of nodes
#SBATCH -J merge
#SBATCH -L SCRATCH          # job requires SCRATCH files
#SBATCH -A m2859          # allocation
#SBATCH -C cpu
#SBATCH -q regular    # regular queue
#SBATCH -t 00:10:00         # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err

export SCRATCH_FOLDER=$SCRATCH/ferredoxin_sim/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export TRIAL=4TNL_merge1
export OUT_DIR=${PWD}
export DIALS_OUTPUT=${SCRATCH}/ferredoxin_sim/${1}

echo "input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform

filter.algorithm=unit_cell
filter.unit_cell.algorithm=cluster
filter.unit_cell.cluster.covariance.file=/global/cfs/cdirs/lcls/sauter/LY99/high_remote_sim/4TNL_covariance_tdata_cells.pickle
filter.unit_cell.cluster.covariance.component=0
filter.unit_cell.cluster.covariance.mahalanobis=4.0
filter.outlier.min_corr=-1.0
select.algorithm=significance_filter
select.significance_filter.sigma=0.1
select.significance_filter.max_ct=300
select.significance_filter.min_ct=200

scaling.model=/global/cfs/cdirs/lcls/sauter/LY99/high_remote_sim/4tnl.pdb
scaling.resolution_scalar=0.993420862158964

postrefinement.enable=True
postrefinement.algorithm=rs
merging.d_min=1.9
merging.merge_anomalous=False
merging.set_average_unit_cell=True
merging.error.model=ev11
statistics.n_bins=20
statistics.report_ML=True
statistics.cciso.mtz_file=/global/cfs/cdirs/lcls/sauter/LY99/high_remote_sim/4tnl-sf.cif
statistics.cciso.mtz_column_F=pdbx_i

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
srun -n 64 -c 2 cctbx.xfel.merge merge.phil
echo "jobend $(date)";pwd

