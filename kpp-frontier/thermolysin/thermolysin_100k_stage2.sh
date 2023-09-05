#!/bin/bash -l
#SBATCH -N 200
#SBATCH -J stage2
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 10
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS=$((SLURM_JOB_NUM_NODES*56))
export SRUN="srun -n $NTASKS --gpus-per-node=8 --cpus-per-gpu=14 --cpu-bind=cores"
echo "running diffBragg stage 2 on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export JOB_ID_INDEX=$1
export JOB_ID_MERGE=$2
export JOB_ID_PREDICT=$3

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export PANDA=$SCRATCH/thermolysin/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export MTZ=${SCRATCH}/thermolysin/${JOB_ID_MERGE}/out/ly99sim_all.mtz

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

export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER
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

echo "jobstart $(date)";pwd
$SRUN simtbx.diffBragg.stage_two stage_two.phil \
    io.output_dir=. \
    pandas_table=$PANDA num_devices=$CCTBX_DEVICE_PER_NODE \
    simulator.structure_factors.mtz_name=$MTZ

echo "jobend $(date)";pwd
