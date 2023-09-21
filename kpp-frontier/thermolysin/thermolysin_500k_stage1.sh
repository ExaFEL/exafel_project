#!/bin/bash -l
#SBATCH -N 256
#SBATCH -J stage1
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 120
#SBATCH -o %j.out
#SBATCH -e %j.err
#export NTASKS_PER_NODE=32
#export NTASKS=$((SLURM_JOB_NUM_NODES * NTASKS_PER_NODE))
#export SRUN="srun -N$SLURM_JOB_NUM_NODES -n$NTASKS -c1 --cpu-bind=cores"
export SRUN="srun -n 4096 -c 3"
echo "running diffBragg stage 1 on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export JOB_ID_SPLIT=$1
export JOB_ID_MERGE=$2

export MTZ=$SCRATCH/thermolysin/${JOB_ID_MERGE}/out/ly99sim_all.mtz
export SPEC=$SCRATCH/thermolysin/${JOB_ID_SPLIT}_integ_exp_ref.txt
export CCTBX_DEVICE_PER_NODE=8
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export DEVICES_PER_NODE=8
export DIFFBRAGG_USE_KOKKOS=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=56
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'
export CCTBX_GPUS_PER_NODE=8

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
env > env.out

echo "
spectrum_from_imageset = True
method = 'L-BFGS-B'
outdir = 'stage1'
debug_mode = False
roi {
  shoebox_size = 10
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
  Nabc = 32 32 32
  G = 1e5
}

refiner {
  num_devices=8
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
$SRUN hopper stage1.phil structure_factors.mtz_name=$MTZ exp_ref_spec_file=$SPEC
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
