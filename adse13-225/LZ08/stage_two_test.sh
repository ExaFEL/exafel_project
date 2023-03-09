#! /bin/bash
#SBATCH -N 2            # Number of nodes
#SBATCH -J stage2       # job name
#SBATCH -A m2859_g      # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:45:00
#SBATCH --gpus 8

. ~/setup.sh
#. /pscratch/sd/i/iris/xfel4/alcc-recipes/cctbx/activate.sh

# to run on 8 GPUs (requested: -N 2 -C GPU --gpus 8):
# working in /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/scale_up
# output in /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_7

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
cd /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_50

srun -n 8 -c 2 --ntasks-per-node=4 --cpu-bind=cores --gpu-bind=cores diffBragg.integrate pred.phil proc_for_pred.phil . reintegrated --numdev 4 --hopInputName pred --cmdlinePhil threshold=1e2
srun -n 8 -c 2 --ntasks-per-node=4 --cpu-bind=cores --gpu-bind=closest ens.hopper reintegrated/pred.pkl stage_two_test.phil --outdir preimport --maxSigma 3 --saveFreq 10  --preImport --refl predicted_refls
srun -n 8 -c 2 --ntasks-per-node=4 --cpu-bind=cores --gpu-bind=cores ens.hopper preimport/preImport_for_ensemble.pkl stage_two_test.phil --outdir global --maxSigma 3 --saveFreq 10 --refl ens.hopper.imported --cmdlinePhil load_data_from_refl=True fix.Nabc=True fix.ucell=True fix.RotXYZ=True fix.Fhkl=False fix.G=False sigmas.G=1e-2
