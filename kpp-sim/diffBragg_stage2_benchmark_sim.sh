#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A lcls_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:36:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH --gpus 128
#SBATCH -o %j.out
#SBATCH -e %j.err

export PERL_NDEV=1  # number GPU per node
export PANDA=$WORK/LS49_output/covariance_ly99sim_cells.pickle
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_CUDA=1

echo "jobstart $(date)";pwd

srun -n 256 -G 128 -c 2 \
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
structure_factors.mtz_name=$SCRATCH/cytochrome_sim/LY99/5993293/out/ly99sim_all.mtz \
structure_factors.mtz_column="Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)" \
min_multiplicity=1

echo "jobend $(date)";pwd