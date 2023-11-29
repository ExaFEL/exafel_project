#!/bin/bash
# with dependency=singleton jobs are linked by userid+jobname and then run in order of submission

nshot=1024 # number of shots to sim
length=6  # length of crystal in micron
Q=debug  # NERSC queue
N=1  # NERSC number of nodes for cytochrome 1 Node per 1000 shots
A=m2859  # NERSC account (_g will automatically be appended for GPU accounts)

# ==========================
n_unrestrain=$((nshot/8))  # number of shots for first pass of stage1
job=cyto_${nshot}img_${length}um  # job name
odir=${CFS}/m2859/cytochrome/${job}  # output results will be here
GPU="-N$N --cpus-per-gpu=8 --ntasks-per-node=32 --gpus-per-node=4 -A${A}_g -Cgpu -q$Q -dsingleton"
CPU="-N$N --ntasks-per-node=32 -A$A -Ccpu -q$Q -dsingleton"
# ==========================

# times calibrated for 1 node per 1024 shots
sbatch -J$job $GPU -t 30 -o${odir}/sim.out -e${odir}/sim.err ./cytochrome_interactive_sim.sh $length $nshot $odir
sbatch -J$job $CPU -t 10 -o${odir}/idx.out -e${odir}/idx.err ./cytochrome_interactive_index.sh $odir
sbatch -J$job $CPU -t  5 -o${odir}/mrg.out -e${odir}/mrg.err ./cytochrome_interactive_merge.sh $odir
sbatch -J$job $CPU -t  5 -o${odir}/spl.out -e${odir}/spl.err ./cytochrome_interactive_split.sh $odir
sbatch -J$job $GPU -t 30 -o${odir}/st1.out -e${odir}/st1.err ./cytochrome_interactive_stage1_restraints_3fold.sh $odir ${n_unrestrain}
sbatch -J$job $GPU -t 30 -o${odir}/prd.out -e${odir}/prd.err ./cytochrome_interactive_predict.sh $odir
sbatch -J$job $GPU -t 30 -o${odir}/st2.out -e${odir}/st2.err ./cytochrome_interactive_stage2.sh $odir
# optional ens.hopper:
# sbatch -J$job $GPU -t 30 -o${odir}/ens.out -e${odir}/ens.err ./cytochrome_interactive_ensHopper.sh $odir
