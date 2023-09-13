#!/bin/bash
#SBATCH -N 32              # Number of nodes
#SBATCH -J stage2          # job name
#SBATCH -A CHM137          # allocation
#SBATCH -p batch           # regular queue
#SBATCH -t 01:30:00        # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n 512 -c 3"

export SCRATCH_FOLDER=$SCRATCH/cytochrome/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export JOB_ID_INDEX=${1}
export JOB_ID_MERGE=${2}
export JOB_ID_PREDICT=${3}

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx/
export MODULES=/lustre/orion/chm137/scratch/vidyagan/

export PERL_NDEV=8  # number GPU per node
export PANDA=$SCRATCH/cytochrome/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
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
space_group=P6522

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
  res_ranges='1.5-999'
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

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"

echo "jobstart $(date)";pwd
$SRUN simtbx.diffBragg.stage_two stage_two.phil \
io.output_dir=${SLURM_JOB_ID} \
pandas_table=${PANDA} num_devices=$PERL_NDEV max_process=65000 \
simulator.structure_factors.mtz_name=${SCRATCH}/cytochrome/${JOB_ID_MERGE}/out/ly99sim_all.mtz
echo "jobend $(date)";pwd
