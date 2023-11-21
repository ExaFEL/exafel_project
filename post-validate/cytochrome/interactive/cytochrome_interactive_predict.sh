#!/bin/bash
nrank=$((12*$SLURM_NNODES))  # 12 tasks per node was critical for kokkos 4+ on Perlmutter
SRUN="srun -n $nrank --ntasks-per-node=12 --cpus-per-gpu=3 --gpus-per-node=4 -c 2"
H5_SIM_PATH=$1
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export HOPPER_RESULTS=${H5_SIM_PATH}/stage1
export SCRATCH_FOLDER=${H5_SIM_PATH}/predict
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export N_START=0
export DEVICES_PER_NODE=4

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
#export DIFFBRAGG_USE_CUDA=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=64
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export MPI4PY_RC_RECV_MPROBE='False'
env > env.out

# copy over the hopper phil
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
  use_diffBragg_mtz = True
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
outdir=.
# if you add the argument --loud, then you will see device timing information in stdout (on rank0 only)
$SRUN diffBragg.integrate pred.phil predict_stage1_kokkos.phil \
    ${HOPPER_RESULTS} $outdir \
    --cmdlinePhil oversample_override=1 \
    predictions.threshold=1 label_weak_col=rlp \ 
    --numdev $DEVICES_PER_NODE --scanWeakFracs
echo "jobend $(date)";pwd

