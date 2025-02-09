#!/bin/bash -l
#SBATCH -N 128             # Number of nodes
#SBATCH --ntasks-per-node=32
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-gpu=8
#SBATCH -J cyto_predict    # job name
#SBATCH -L SCRATCH         # job requires SCRATCH files
#SBATCH -A m2859_g         # allocation
#SBATCH -C gpu
#SBATCH -q regular         # regular or special queue
#SBATCH -t 00:15:00        # wall clock time limit
#SBATCH --gpus-per-node 4
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -c 4"

export SCRATCH_FOLDER=$SCRATCH/cytochrome/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export JOB_ID_HOPPER=$1
export HOPPER_RESULTS=$SCRATCH/cytochrome/$JOB_ID_HOPPER/stage1

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
export NUMEXPR_MAX_THREADS=64
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export MPI4PY_RC_RECV_MPROBE='False'
env > env.out

cat $HOPPER_RESULTS/diff.phil > pred.phil
echo "
debug_mode = False
predictions {
  verbose = False
  laue_mode = False
  qcut = 0.0035
  label_weak_col = 'rlp'
  oversample_override = 1
  Nabc_override = None
  pink_stride_override = None
  resolution_range = [1.5,999]
  symbol_override = P6522
  method = *diffbragg exascale
  use_peak_detection = False
  weak_fraction = 1
}
" >> pred.phil

echo "
spotfinder.threshold.algorithm=dispersion
spotfinder.threshold.dispersion.gain=1
spotfinder.threshold.dispersion.global_threshold=40
spotfinder.threshold.dispersion.kernel_size=[2,2]
spotfinder.threshold.dispersion.sigma_strong=1
spotfinder.threshold.dispersion.sigma_background=6
spotfinder.filter.min_spot_size=2

indexing.method=fft1d
indexing.known_symmetry.unit_cell=77.856,77.856,263.615,90,90,120
indexing.known_symmetry.space_group=P6522
indexing.stills.set_domain_size_ang_value=500

integration.summation.detector_gain=1

# Later substitute in the actual index.phil from the preceeding job
" > predict_stage1_kokkos.phil

echo "jobstart $(date)";pwd
$SRUN diffBragg.integrate pred.phil predict_stage1_kokkos.phil \
    "${HOPPER_RESULTS}" predict \
    --cmdlinePhil oversample_override=1 \
    predictions.threshold=1 label_weak_col=rlp \
    --numdev $CCTBX_DEVICE_PER_NODE --scanWeakFracs
echo "jobend $(date)";pwd
