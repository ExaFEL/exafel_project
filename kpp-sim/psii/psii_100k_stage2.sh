#!/bin/bash

#SBATCH -N 128            # Number of nodes
#SBATCH --ntasks-per-node=32
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-gpu=4
#SBATCH -J stage2        # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m2859_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 2:00:00
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -N128 --ntasks-per-node=32 --gpus-per-node=4 --cpus-per-gpu=4 -c4"

export SCRATCH_FOLDER=$SCRATCH/psii/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export JOB_ID_INDEX=${1}
export JOB_ID_MERGE=${2}
export JOB_ID_PREDICT=${3}

export PERL_NDEV=4  # number GPU per node
export PANDA=$SCRATCH/psii/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt

export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=1
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

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
space_group=P212121

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
  res_ranges='1.9-999'
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
  logfiles = True
}
" > stage_two.phil

echo "jobstart $(date)";pwd
$SRUN simtbx.diffBragg.stage_two stage_two.phil \
io.output_dir=${SLURM_JOB_ID} \
pandas_table=${PANDA} num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=${SCRATCH}/psii/${JOB_ID_MERGE}/out/ly99sim_all.mtz \

echo "jobend $(date)";pwd
