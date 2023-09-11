#!/bin/bash -l
#SBATCH -N 512
#SBATCH -J predict
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 15
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS_PER_NODE=56
export NTASKS=$((SLURM_JOB_NUM_NODES * NTASKS_PER_NODE))
export NODELIST=`scontrol show hostnames $SLURM_NODELIST`

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER
echo "#! /bin/bash
echo \"reporting from task \$SLURM_LOCALID of \$SLURM_NTASKS on node \$SLURM_NODEID of \$SLURM_NNODES running on \$SLURMD_NODENAME\"
" > check_nodes.sh
chmod +x check_nodes.sh

srun -N $SLURM_NNODES -n${NTASKS} -c1 -t2 ./check_nodes.sh > node_report.out

if [ -f "nodelist_ok" ]; then rm nodelist_ok; fi
if [ -f "nodelist_exclude" ]; then rm nodelist_exclude; fi
for nodename in $NODELIST; do
        export count=`grep "running on $nodename" node_report.out | wc -l`
        if [ ! "$count" == "$NTASKS_PER_NODE" ]
                then
                        echo "exclude node $nodename"
                        echo -n "$nodename," >> nodelist_exclude
                else
                        echo "node $nodename OK"
                        echo -n "$nodename," >> nodelist_ok
        fi
done

#export SLURM_STEP_NODELIST=$(cat nodelist_ok)
export STEP_NNODES=`sed "s:,: :g" nodelist_ok | wc -w`
export NTASKS=$((STEP_NNODES * NTASKS_PER_NODE))
if [ -f "nodelist_exclude" ]; then
        export EXCLUDE="--exclude=$(cat nodelist_exclude)"
fi

export SRUN="srun -N$STEP_NNODES -n$NTASKS -c1 $EXCLUDE --cpu-bind=cores"
echo "predicting/integrating on $STEP_NNODES nodes with $SRUN"

export JOB_ID_HOPPER=$1

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

echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
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
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
