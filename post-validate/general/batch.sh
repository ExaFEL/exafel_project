#!/bin/bash
# with dependency=singleton jobs are linked by userid+jobname and then run in order of submission

sample=$1 # must be one of cyto yb_lyso cry11ba thermo
n_thousand=$2 # number of shots to sim
length=$3  # length of crystal in micron
detdist=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['off'])"`
pdb=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['pdb'])"`
dmin=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['dmin'])"`
spcgrp=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['spcgrp'])"`
ucell=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['ucell'])"`
cov=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['cov'])"`
sigu=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['sigu'])"`


echo "Initializing diffBragg analysis of $n_thousand thousands of $sample crystals, $length um in length,"

# SLURM settings
Q=regular  # NERSC queue
A=m2859  # NERSC account for the ExaFEL project (_g will automatically be appended for GPU accounts)

nshot=$((1024*n_thousand)) # number of shots to sim (always multiples of 1024)
N=$((1*n_thousand))  # NERSC number of nodes: 1 node/1000 shots (Q=regular); 2 nodes/1000 shots (Q=debug)
n_unrestrain=$((nshot/8))  # number of shots for first pass of stage1
job=${sample}_${n_thousand}Kimg_${length}um  # job name
odir=${SCRATCH}/m2859/$sample/${job}  # output results will be here
GPU="-N$N --cpus-per-gpu=8 --ntasks-per-node=32 --gpus-per-node=4 -A${A}_g -Cgpu -q$Q -dsingleton"
CPU="-N$N --ntasks-per-node=32 -A$A -Ccpu -q$Q -dsingleton"

echo "GPU settings: "$GPU
echo "CPU settings: "$CPU
echo "Jobname: "$job
echo "output root: "$odir

mkdir -p ${odir}
# times calibrated for 1 node per 1024 shots
echo sim for $sample $nshot $length um $detdist $pdb $odir
sbatch -J$job $GPU -t 50 -o${odir}/sim.out -e${odir}/sim.err ./general_sim.sh $length $nshot $detdist $pdb $odir
echo index for $dmin $spcgrp $ucell $odir
sbatch -J$job $CPU -t 60 -o${odir}/idx.out -e${odir}/idx.err ./general_index.sh $dmin $spcgrp $ucell $odir
echo merge for $cov $pdb $dmin $odir
sbatch -J$job $CPU -t 20 -o${odir}/mrg.out -e${odir}/mrg.err ./general_merge.sh $cov $pdb $dmin $odir
sbatch -J$job $CPU -t 20 -o${odir}/spl.out -e${odir}/spl.err ./general_split.sh $odir
echo stage1 $sigu $spcgrp $odir ${n_unrestrain}
sbatch -J$job $GPU -t 60 -o${odir}/st1.out -e${odir}/st1.err ./general_stage1_restraints_3fold.sh $sigu $spcgrp $odir ${n_unrestrain}
echo predict $dmin $spcgrp $ucell $odir
sbatch -J$job $GPU -t 60 -o${odir}/prd.out -e${odir}/prd.err ./general_predict.sh $dmin $spcgrp $ucell $odir
sbatch -J$job $GPU -t 120 -o${odir}/st2.out -e${odir}/st2.err ./general_stage2.sh $dmin $odir
# optional ens.hopper:
sbatch -J$job $GPU -t 120 -o${odir}/ens.out -e${odir}/ens.err ./general_ensHopper.sh $dmin $odir
