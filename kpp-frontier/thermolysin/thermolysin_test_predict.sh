#!/bin/bash -l
#SBATCH -N 4
#SBATCH -J predict
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 5
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS=$((SLURM_JOB_NUM_NODES*56))
export SRUN="srun -n $NTASKS --gpus-per-node=8 --cpus-per-gpu=14 --cpu-bind=cores"
echo "predicting/integrating on $SLURM_JOB_NUM_NODES nodes with $SRUN"

export JOB_ID_HOPPER=$1

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export HOPPER_RESULTS=$SCRATCH/thermolysin/$JOB_ID_HOPPER/stage1

export CCTBX_DEVICE_PER_NODE=8

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
simulator.detector.force_zero_thickness=True
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
debug_mode = False
predictions {
  verbose = False
  laue_mode = False
  qcut = 0.0035
  label_weak_col = 'rlp'
  weak_fraction = 0.67
  threshold = 1
  oversample_override = 2
  Nabc_override = None
  pink_stride_override = 10
  default_Famplitude = 1e3
  resolution_range = [1.7,999]
  symbol_override = P6122
  method = *diffbragg exascale
  use_peak_detection = False
}
" > pred.phil

echo "
spotfinder.threshold.algorithm=dispersion
spotfinder.threshold.dispersion.gain=1
spotfinder.threshold.dispersion.global_threshold=40
spotfinder.threshold.dispersion.kernel_size=[2,2]
spotfinder.threshold.dispersion.sigma_strong=1
spotfinder.threshold.dispersion.sigma_background=6
spotfinder.filter.min_spot_size=2

indexing.method=fft1d
indexing.known_symmetry.unit_cell=93, 93,130.4,90,90,120
indexing.known_symmetry.space_group=P6122
indexing.stills.set_domain_size_ang_value=500

integration.summation.detector_gain=1

# Later substitute in the actual index.phil from the preceeding job
" > predict_stage1_kokkos.phil

echo "jobstart $(date)";pwd

$SRUN diffBragg.integrate pred.phil predict_stage1_kokkos.phil $HOPPER_RESULTS predict \
    --cmdlinePhil oversample_override=1 Nabc_override=[52,52,52] threshold=1 label_weak_col=rlp \
    --numdev $CCTBX_DEVICE_PER_NODE

echo "jobend $(date)";pwd
