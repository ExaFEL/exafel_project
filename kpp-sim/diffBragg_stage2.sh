#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 01:30:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH --gpus 128
#SBATCH -o %j.out
#SBATCH -e %j.err

export PERL_NDEV=1  # number GPU per node
export PANDA=$SCRATCH/ferredoxin_sim/$1/out/$2.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
# export DIFFBRAGG_USE_CUDA=1
export DIFFBRAGG_USE_KOKKOS=1

echo "jobstart $(date)";pwd

srun -n 256 -G 128 -c 16 \
simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil \
io.output_dir=$SLURM_JOB_ID \
pandas_table=$PANDA num_devices=$PERL_NDEV \
exp_ref_spec_file = $WORK/exafel_output/exp_ref_spec \
structure_factors.mtz_name = $SCRATCH/ferredoxin_sim/$3/out/ly99sim_all.mtz \
refiner.reference_geom=$GEOM \

echo "jobend $(date)";pwd