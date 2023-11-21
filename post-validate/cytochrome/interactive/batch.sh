#!/bin/bash
# with dependency=singleton jobs are linked by userid+jobname and then run in order of submission

nshot=65536 # number of shots to sim
length=4  # length of crystal in micron
n_unrestrain=$((nshot/8))  # number of shots for first pass of stage1
job=cyto_${nshot}_${length}  # job name
odir=$SCRATCH/cytochrome/$job  # output results will be here
GPU="-N64 --cpus-per-gpu=8 --ntasks-per-node=32 --gpus-per-node=4 -Am2859_g -Cgpu -qregular -dsingleton"
CPU="-N64 --ntasks-per-node=64 -Am2859 -Ccpu -qregular -dsingleton"

sbatch -J$job $GPU -t 40 -o${odir}/sim.out -e${odir}/sim.err ./cytochrome_interactive_sim $length $nshot $job
sbatch -J$job $CPU -t 10 -o${odir}/idx.out -e${odir}/idx.err ./cytochrome_interactive_index.sh $odir
sbatch -J$job $CPU -t  5 -o${odir}/mrg.out -e${odir}/mrg.err ./cytochrome_interactive_merge.sh $odir
sbatch -J$job $CPU -t  5 -o${odir}/spl.out -e${odir}/spl.err ./cytochrome_interactive_split.sh $odir
sbatch -J$job $GPU -t 40 -o${odir}/st1.out -e${odir}/st1.err ./cytochrome_interactive_stage1_restraints_3fold.sh $odir ${n_unrestrain}
sbatch -J$job $GPU -t 40 -o${odir}/prd.out -e${odir}/prd.err ./cytochrome_interactive_predict.sh $odir
sbatch -J$job $GPU -t 40 -o${odir}/st2.out -e${odir}/st2.err ./cytochrome_interactive_stage2.sh $odir
# optional ens.hopper:
sbatch -J$job $GPU -t240 -o${odir}/ens.out -e${odir}/ens.err ./cytochrome_interactive_ensHopper.sh $odir
