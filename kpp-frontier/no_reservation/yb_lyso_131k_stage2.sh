#!/bin/bash
#SBATCH -N 80            # Number of nodes
#SBATCH -J multisrun     # job name
#SBATCH -A CHM137        # allocation
#SBATCH -p batch         # regular partition
#SBATCH -t 120
#SBATCH -o %j.out
#SBATCH -e %j.err
export SRUN="srun -N 16 -n 256 -c 3" # run five srun jobs at once

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/no_reservation/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export PERL_NDEV=8  # number GPU per node
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt

export CCTBX_DEVICE_PER_NODE=8
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=8
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=32
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=8
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

echo "
max_sigz=4.0
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 10
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
}
space_group=P43212

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
  num_devices = 4
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
  logfiles = False # True for memory troubleshooting but consumes 3 seconds of wall time
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
export job_ids_arr=(
1427014 1427835 1428320
1427017 1427900 1428322
1411658 1427901 1428333
1427020 1427902 1428365
1427035 1427903 1428853)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/yb_lyso/${JOB_ID_MERGE}/out/yb_lyso_500k_all.mtz
  export PANDA=$SCRATCH/yb_lyso/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  echo "#! /bin/bash
echo \"jobstart job \$(date)\" > job${job}.out 2> job${job}.err
pwd >> job${job}.out 2>> job${job}.err
$SRUN simtbx.diffBragg.stage_two stage_two.phil \
io.output_dir=${SLURM_JOB_ID}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV max_process=30000 \
simulator.structure_factors.mtz_name=$MTZ >> job${job}.out 2>> job${job}.err
echo \"jobend \$(date)\" >> job${job}.out 2>> job${job}.err
pwd >> job${job}.out 2>> job${job}.err
" > job${job}.sh
  chmod +x job${job}.sh
  ./job${job}.sh &
done
wait

