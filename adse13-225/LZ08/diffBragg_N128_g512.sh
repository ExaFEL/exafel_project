#! /bin/bash
#SBATCH -N 128          # Number of nodes
#SBATCH -J test         # job name
#SBATCH -A m2859_g      # allocation
#SBATCH -C gpu
#SBATCH -C gpu&hbm80g   # high memory nodes (up to 256)
#SBATCH -q regular
#SBATCH -t 00:45:00
#SBATCH --gpus 512

# this hit error slurmstepd: error: Detected 1 oom-kill event(s) in StepId=6055443.1. Some of your processes may have been killed by the cgroup out-of-memory handler.

# Number of images to subsample
export n_sample=6400

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
export OMP_PROC_BIND=spread

echo "Processing $n_sample images."
export phil_dir=/pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/scale_up
echo "Working with $SLURM_NNODES nodes and $SLURM_GPUS GPUs. There should be 4 GPUs per node."
export n_tasks=$SLURM_GPUS
echo "Executing srun jobs with $n_tasks tasks (-n). This should match 4 tasks per node."
export cpus_per_task=32
echo "Using $cpus_per_task CPUs per task. This should match 2 * floor(64/tasks_per_node)."

export OMP_DISPLAY_AFFINITY=true
export OMP_AFFINITY_FORMAT="host=%H, pid=%P, thread_num=%n, thread affinity=%A"

echo "jobstart $(date)";pwd

mkdir /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_${n_sample}
cd /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v4/trials/scale_${n_sample}

mkdir stage_one
cp $phil_dir/stage_one_test.phil .
#head -$n_sample /pscratch/sd/c/cctbx/cxilz0820/common/diffbragg/v2/best500_spec_file.out > spec_file.out
head -$n_sample /pscratch/sd/c/cctbx/cxilz0820/common/results/trial_000_rg004_task021_reproduce_spec_file.out > spec_file.out

srun -n $n_tasks -c $cpus_per_task \
simtbx.diffBragg.hopper stage_one_test.phil

echo "stage one completed at $(date)";pwd

cp $phil_dir/stage_two_test.phil .
cp $phil_dir/simulation.phil .
cp $phil_dir/sim_processing.phil .

srun -n $n_tasks -c $cpus_per_task \
diffBragg.integrate simulation.phil sim_processing.phil stage_one reintegrated \
--numdev 4 --hopInputName pred --cmdlinePhil threshold=1e2

srun -n $n_tasks -c $cpus_per_task \
ens.hopper reintegrated/pred.pkl stage_two_test.phil \
--outdir preimport --maxSigma 3 --saveFreq 10  --preImport --refl predicted_refls

srun -n $n_tasks -c $cpus_per_task \
ens.hopper preimport/preImport_for_ensemble.pkl stage_two_test.phil \
--outdir global --maxSigma 3 --saveFreq 10 --refl ens.hopper.imported \
--cmdlinePhil fix.Nabc=True fix.ucell=True fix.RotXYZ=True fix.Fhkl=False fix.G=False sigmas.G=1e-2

echo "stage two completed at $(date)";pwd
