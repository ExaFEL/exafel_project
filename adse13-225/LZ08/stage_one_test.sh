#! /bin/bash
#SBATCH -N 2            # Number of nodes
#SBATCH -J stage1       # job name
#SBATCH -A m2859_g      # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 01:45:00
#SBATCH --gpus 8

. /pscratch/sd/i/iris/xfel4/alcc-recipes/cctbx/activate.sh

export SIT_DATA=/global/common/software/lcls/psdm/data
export SIT_PSDM_DATA=/pscratch/sd/p/psdatmgr/data/pmscr
export DIFFBRAGG_USE_CUDA=1
export HDF5_USE_FILE_LOCKING=FALSE
export MPI4PY_RC_RECV_MPROBE='False'
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PLACES=threads

export phil_dir=/pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/scale_up
# Number of images to subsample
export n_sample=1000

echo "jobstart $(date)";pwd
echo "using $n_sample images"

mkdir /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_${n_sample}
cd /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_${n_sample}

mkdir stage_one
cp $phil_dir/stage_one_test.phil .
# for full set use the next line instead of the best500 spec file (not a good idea for small subsets)
#head -$n_sample /pscratch/sd/c/cctbx/cxilz0820/common/results/trial_000_rg004_task021_reproduce_spec_file.out > spec_file.out
head -$n_sample /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v2/best500_spec_file.out > spec_file.out

srun -n 8 -c 2 --ntasks-per-node=4 --cpu-bind=cores --gpu-bind=cores \
simtbx.diffBragg.hopper stage_one_test.phil

echo "stage one completed at $(date)";pwd
