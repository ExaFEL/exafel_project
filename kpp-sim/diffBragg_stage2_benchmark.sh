#!/bin/bash -l
#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A lcls_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:36:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=8
#SBATCH -o %j.out
#SBATCH -e %j.err

export PERL_NDEV=1  # number GPU per node
export PANDA=$MODULES/diffbragg_benchmarks/AD_SE_13_222/data_222/8_stage2_7_gathered_trimmed.pkl
export GEOM=$MODULES/diffbragg_benchmarks/AD_SE_13_222/data_222/Jungfrau_model.json
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_CUDA=1

export CCTBX_DEVICE_PER_NODE=1
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=1
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_CUDA=1
export CUDA_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=1
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path


echo "jobstart $(date)";pwd

srun -n 1024 -G 32 -c 2 \
simtbx.diffBragg.stage_two \
$MODULES/diffbragg_benchmarks/AD_SE_13_222/data_222.phil \
io.output_dir=$SLURM_JOB_ID \
pandas_table=$PANDA \
num_devices=$PERL_NDEV \
logfiles=True \
profile=True \
prep_time=90 \
logging.disable=False \
max_calls=[501] \
save_model_freq=250 \
refiner.load_data_from_refl=True \
refiner.reference_geom=$GEOM \
structure_factors.mtz_name=$MODULES/diffbragg_benchmarks/AD_SE_13_222/100shuff.mtz \
structure_factors.mtz_column="F(+),SIGF(+),F(-),SIGF(-)" \
min_multiplicity=1

echo "jobend $(date)";pwd