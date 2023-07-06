#!/bin/bash

#SBATCH -N 32            # Number of nodes
#SBATCH -J stage_2_32       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH --cpus-per-task=16
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-node=4
#SBATCH -o %j.out
#SBATCH -e %j.err

export JOB_ID_INTEGRATE=$1 
export PKL_FILE=$2
export JOB_ID_MERGE=$3

export PERL_NDEV=4  # number GPU per node
export PANDA=$SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out/${PKL_FILE}.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
# export DIFFBRAGG_USE_CUDA=1
export DIFFBRAGG_USE_KOKKOS=1
export MPI4PY_RC_RECV_MPROBE=False

echo "jobstart $(date)";pwd

srun -N 32 --ntasks-per-node=8 --cpus-per-gpu=2 --gpus-per-node=4 simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=$SLURM_JOB_ID pandas_table=$PANDA num_devices=$PERL_NDEV exp_ref_spec_file=$WORK/exafel_output/exp_ref_spec structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz refiner.reference_geom=$GEOM

echo "jobend $(date)";pwd

