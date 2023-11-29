#!/bin/bash
# with dependency=singleton jobs are linked by userid+jobname and then run in order of submission

# command line args:
n_thousand=$1  # an integer from >= 1.  Set to e.g., 64 to simulate 64*1024 shots
length=$2  # length of crystal in micron
tag=$3  # a tag for the output folder
# other settings
Q=regular  # NERSC queue
A=m2859  # NERSC account (_g will automatically be appended for GPU accounts)

nshot=$((1024*n_thousand)) # number of shots to sim (always multiples of 1024)
N=$((1*n_thousand))  # NERSC number of nodes for cytochrome 2 Node per 1024 shots
n_unrestrain=$((nshot/8))  # number of shots for first pass of stage1
job=${tag}_${nshot}img_${length}um  # job name
odir=${CFS}/m2859/cytochrome/${job}  # output results will be here
GPU="-N$N --cpus-per-gpu=8 --ntasks-per-node=32 --gpus-per-node=4 -A${A}_g -Cgpu -q$Q -dsingleton"
CPU="-N$N --ntasks-per-node=32 -A$A -Ccpu -q$Q -dsingleton"

echo "GPU settings: "$GPU
echo "CPU settings: "$CPU
echo "Jobname: "$job
echo "output root: "$odir

# times (in MINUTES) estimated for 1 nodes per 1024 shots
tsim=50  # simulation
tidx=60  # indexing with stills process
tmrg=20  # merging
tspl=20  # splitting
tst1=60  # stage1 (hopper)
tprd=60  # prediction
tst2=120  # stage2
tens=120  # stage2 (ensemble hopper)

# NOTE: CPU partition causing failures with many nodes.
#  I had to switch all $CPU to $GPU below for index, merge, split steps

# submit:
sbatch -J$job $GPU -t $tsim -o${odir}/sim.out -e${odir}/sim.err ./cytochrome_interactive_sim.sh $length $nshot $odir
sbatch -J$job $CPU -t $tidx -o${odir}/idx.out -e${odir}/idx.err ./cytochrome_interactive_index.sh $odir
sbatch -J$job $CPU -t $tmrg -o${odir}/mrg.out -e${odir}/mrg.err ./cytochrome_interactive_merge.sh $odir
sbatch -J$job $CPU -t $tspl -o${odir}/spl.out -e${odir}/spl.err ./cytochrome_interactive_split.sh $odir
sbatch -J$job $GPU -t $tst1 -o${odir}/st1.out -e${odir}/st1.err ./cytochrome_interactive_stage1_restraints_3fold.sh $odir ${n_unrestrain}
sbatch -J$job $GPU -t $tprd -o${odir}/prd.out -e${odir}/prd.err ./cytochrome_interactive_predict.sh $odir
sbatch -J$job $GPU -t $tst2 -o${odir}/st2.out -e${odir}/st2.err ./cytochrome_interactive_stage2.sh $odir
sbatch -J$job $GPU -t $tens -o${odir}/ens.out -e${odir}/ens.err ./cytochrome_interactive_ensHopper.sh $odir

nodehr=$(((tsim+tidx+tmrg+tspl+tst1+tprd+tst2+tens)*N/60))
echo "Estimated node hours (multiply by 2 if using priority queue): "$nodehr
