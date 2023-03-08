#!/bin/bash

#SBATCH -N 2            # Number of nodes
#SBATCH -J lz08hop      # job name
#SBATCH -A m3890_g      # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:45:00
#SBATCH --gpus 8

#. /pscratch/sd/i/iris/xfel4/alcc-recipes/cctbx/activate.sh
. ~/setup.sh

export SIT_DATA=/global/common/software/lcls/psdm/data
export SIT_PSDM_DATA=/pscratch/sd/p/psdatmgr/data/pmscr
#export NERSC_SIT_PSDM_DATA=/pscratch/sd/p/psdatmgr/data/pmscr
#export PERL_NDEV=4  # number GPU per node
#export IBV_FORK_SAFE=1 
#export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_CUDA=1
export HDF5_USE_FILE_LOCKING=FALSE
export MPI4PY_RC_RECV_MPROBE='False'
#export CCTBX_NO_UUID=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
#export OMP_PROC_BIND=spread
#export OMP_PROC_BIND=TRUE
export OMP_PLACES=threads
#export CCTBX_GPUS_PER_NODE=1

echo "jobstart $(date)";pwd

srun -n 8 -c 2 --ntasks-per-node=4 --cpu-bind=cores --gpu-bind=cores \
simtbx.diffBragg.hopper stage_one_test.phil
export outdir=`grep outdir stage_one_test.phil | sed "s:.* ::; s:\"::g"`
touch $outdir/DONE

echo "jobend $(date)";pwd

