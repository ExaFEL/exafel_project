#!/bin/bash

#SBATCH -N 64            # Number of nodes
#SBATCH --ntasks-per-node=16
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-gpu=4
#SBATCH -J stage_1       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m2859_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 02:00:00
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -N64 --ntasks-per-node=16 --gpus-per-node=4 --cpus-per-gpu=4 -c2"

export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

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
method = 'L-BFGS-B'
outdir = 'stage1'
debug_mode = False
roi {
  shoebox_size = 15
  fit_tilt = True
  reject_edge_reflections = False
  reject_roi_with_hotpix = False
  pad_shoebox_for_background_estimation = 0
  fit_tilt_using_weights = False
  mask_outside_trusted_range = True
}

fix {
  detz_shift = True
  ucell=False
  Nabc=False
  G=False
  RotXYZ=False
}

sigmas {
  ucell = .1 .1
  RotXYZ = 0.01 0.01 0.01
  G = 1
  Nabc = 1 1 1
}

init {
  Nabc = 52 52 52
  G = 1e5
}

refiner {
  num_devices=4
  verbose = 0
  sigma_r = 3
  adu_per_photon = 1
  #reference_geom = '${MODULES}/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt'
}

simulator {
  oversample = 1
  crystal.has_isotropic_ncells = False
  structure_factors {
    mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  }
  beam {
    size_mm = 0.001
  }
  detector {
    force_zero_thickness = True
  }
}

mins {
  detz_shift = -1.5
  RotXYZ = -15 -15 -15
}
maxs {
  detz_shift = 1.5
  Nabc = 1600 1600 1600
  RotXYZ = 15 15 15
}
ucell_edge_perc = 15
ucell_ang_abs = 1
space_group = P6122
use_restraints = False
logging {
  rank0_level = low normal *high
}
downsamp_spec {
  skip = True
}
" > stage1.phil

echo "jobstart $(date)";pwd
$SRUN hopper stage1.phil structure_factors.mtz_name=$1 exp_ref_spec_file=$2
echo "jobend $(date)";pwd
