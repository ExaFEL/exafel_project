#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A m2859_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 01:30:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH --gpus 128
#SBATCH -o %j.out
#SBATCH -e %j.err

export PERL_NDEV=1  # number GPU per node
export PANDA=$SCRATCH/ferredoxin_sim/9713113/out/preds_for_hopper.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
# export DIFFBRAGG_USE_CUDA=1
export DIFFBRAGG_USE_KOKKOS=1

echo "jobstart $(date)";pwd

srun -n 256 -G 128 -c 16 \
simtbx.diffBragg.stage_two \
$MODULES/exafel_project/kpp-sim/diffBragg_stage2.phil \
io.output_dir=$SLURM_JOB_ID \
pandas_table=$PANDA \
num_devices=$PERL_NDEV \
logfiles=True \
profile=True \
prep_time=90 \
logging.disable=False \
max_calls=[11] \
save_model_freq=5 \
refiner.load_data_from_refl=True \
refiner.reference_geom=$GEOM \
structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/9521300/out/ly99sim_all.mtz \
structure_factors.mtz_column="Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)" \
min_multiplicity=1

echo "jobend $(date)";pwd