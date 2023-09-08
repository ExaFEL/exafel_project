#!/bin/bash
#SBATCH -N 512             # Number of nodes
#SBATCH -J predict         # job name
#SBATCH -A CHM137          # allocation
#SBATCH -p batch           # regular queue
#SBATCH -t 0:30:00         # wall clock time limit
#SBATCH -o %j.out
#SBATCH -e %j.err
SRUN="srun -n 8192 -c 3"

export SCRATCH_FOLDER=$SCRATCH/cytochrome/$SLURM_JOB_ID
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

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
export NUMEXPR_MAX_THREADS=32
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

# possible extension, use the index.phil; export JOB_ID_INDEX=$2
export JOB_ID_HOPPER=$1

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
  weak_fraction = 0.33
  threshold = 10
  oversample_override = 1
  Nabc_override = None
  pink_stride_override = 10
  default_Famplitude = 1e3
  resolution_range = [1.5,999]
  symbol_override = P6522
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
indexing.known_symmetry.unit_cell=77.856,77.856,263.615,90,90,120
indexing.known_symmetry.space_group=P6522
indexing.stills.set_domain_size_ang_value=500

integration.summation.detector_gain=1

# Later substitute in the actual index.phil from the preceeding job
" > predict_stage1_kokkos.phil

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"

echo "jobstart $(date)";pwd
$SRUN diffBragg.integrate pred.phil predict_stage1_kokkos.phil \
$SCRATCH/cytochrome/$JOB_ID_HOPPER/stage1 \
predict \
--cmdlinePhil oversample_override=1 \
Nabc_override=[29,29,29] threshold=1 label_weak_col=rlp \
--numdev 8
libtbx.python -c "import pandas; df = pandas.read_pickle('predict/preds_for_hopper.pkl'); print('pickled',len(df))"
echo "jobend $(date)";pwd
