#!/bin/bash -l
#SBATCH -N 1280
#SBATCH -J stage2
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 120
#SBATCH -o %j.out
#SBATCH -e %j.err
export SRUN="srun -N 256 -n 4096 -c2" # five sruns can run simultaneously in this batch job

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/no_reservation/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export PERL_NDEV=8

export CCTBX_DEVICE_PER_NODE=8
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1

export DIFFBRAGG_USE_KOKKOS=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=56
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'
export CCTBX_GPUS_PER_NODE=8

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes3.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
env > env.out

echo "
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 15
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
}
space_group=P6122

sigmas {
  G = 1
  Fhkl = 1
}

refiner {
  refine_Fcell = [1]
  #refine_Nabc = [1]
  refine_spot_scale = [1]
  max_calls = [450]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 3
  num_devices = 8
  adu_per_photon = 1
  res_ranges='1.75-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

simulator {
  crystal.has_isotropic_ncells = False
  #structure_factors.mtz_name = merged/iobs_all.mtz
  structure_factors.mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  beam.size_mm = 0.001
  detector {
    force_zero_thickness = True
  }
}

logging {
  rank0_level = low normal *high
  logfiles = False
}
" > stage_two.phil

# copy program to nodes
echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes3.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"

# run program for each ordered set of job IDs matching one crystal size
# each row is one job's index, merge, and predict job IDs, in that order
# rows are 20, 10, 5, 2, 1, and 0.5 micron crystal sizes, in that order
# (0.5 micron size is dropped for 5-srun batch job)
export job_ids_arr=(
1433992 1435935 1444175
1430293 1435907 1444174
1431151 1435356 1444173
1431150 1450095 1452682
1431149 1434920 1443110)
#1432661 1434903 1437231)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/thermolysin/${JOB_ID_MERGE}/out/ly99sim_all.mtz
  export PANDA=$SCRATCH/thermolysin/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  echo "#! /bin/bash
echo \"jobstart job \$(date)\" > job${job}.out 2> job${job}.err
pwd >> job${job}.out 2>> job${job}.err
echo \"running stage 2 on 524k thermolysin images with command $SRUN\"
$SRUN simtbx.diffBragg.stage_two stage_two.phil \
io.output_dir=${SLURM_JOB_ID}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=$MTZ >> job${job}.out 2>> job${job}.err
echo \"jobend \$(date)\" >> job${job}.out 2>> job${job}.err
pwd >> job${job}.out 2>> job${job}.err
" > job${job}.sh
  chmod +x job${job}.sh
  ./job${job}.sh &
done
wait


