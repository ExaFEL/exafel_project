#!/bin/bash

#SBATCH -N 128            # Number of nodes
#SBATCH -J stage_2_128       # job name
#SBATCH -L SCRATCH       # job requires SCRATCH files
#SBATCH -A nstaff_g       # allocation
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 00:26:00
#SBATCH --gpus-per-node=4
#SBATCH --ntasks-per-gpu=2
#SBATCH --gpus 512

export PERL_NDEV=1  # number GPU per node
export PANDA=$PSCRATCH/diffbragg_benchmarks/work/data_222/8_stage2_7_gathered_trimmed.pkl
export GEOM=$PSCRATCH/diffbragg_benchmarks/work/data_222/Jungfrau_model.json
export IBV_FORK_SAFE=1 
export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_KOKKOS=1

echo "jobstart $(date)";pwd

srun -n 1024 -G 512 -c 2 \
simtbx.diffBragg.stage_two \
$PSCRATCH/diffbragg_benchmarks/AD_SE_13_222/data_222.phil \
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
structure_factors.mtz_name=$PSCRATCH/diffbragg_benchmarks/AD_SE_13_222/100shuff.mtz \
structure_factors.mtz_column="F(+),SIGF(+),F(-),SIGF(-)" \
min_multiplicity=1

echo "jobend $(date)";pwd

