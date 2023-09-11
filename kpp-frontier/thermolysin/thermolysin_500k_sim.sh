#!/bin/bash -l
#SBATCH -N 256
#SBATCH -J sim
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 60
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS_PER_NODE=32
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
export N_SIM=524288 # total number of images to simulate
export LENGTH=$1
echo "simulating $N_SIM images of xtal length $LENGTH um on $STEP_NNODES nodes with $SRUN"

export CCTBX_DEVICE_PER_NODE=8
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=8
export MOS_DOM=25

export DIFFBRAGG_USE_KOKKOS=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=56
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'
export CCTBX_GPUS_PER_NODE=8

mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER
echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
env > env.out

echo "
noise=True
psf=False
attenuation=True
context=kokkos_gpu
absorption=high_remote
oversample=1
beam {
  mean_energy=9500.
}
spectrum {
  nchannels=100
  channel_width=1.0
}
crystal {
  # Perlmutter OK-download in job from PDB
  # structure=pdb
  # pdb.code=4tnl # thermolysin
  # Frontier OK-take PDB file from github
  structure=pdb
  pdb.code=None
  pdb.source=file
  pdb.file=${MODULES}/exafel_project/kpp-sim/thermolysin/4tnl.pdb
  length_um=${LENGTH} # increase crystal path length # <-- change this to vary xtal size (depending on diffraction limit... increase if it's weak diffraction at detector edges, decr otherwise. probably a set of 5 xtal sizes between 10 and 0.2 um)
}
detector {
  tiles=multipanel
  reference=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
  offset_mm=80.0 # desired 1.8 somewhere between inscribed and circumscribed.
}
output {
  format=h5
  ground_truth=${SCRATCH_FOLDER}/ground_truth.mtz
}
" > trial.phil

echo "jobstart $(date)";pwd
$SRUN libtbx.python $MODULES/exafel_project/kpp_utils/LY99_batch.py trial.phil
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
