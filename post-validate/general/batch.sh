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
nabc=`libtbx.python -c "from exafel_project.kpp_utils.cases import cases; print(cases['$sample']['nabc'])"`
echo "Initializing diffBragg analysis of $n_thousand thousands of $sample crystals, $length um in length,"

# If $4 is given, it must be a string of digits including steps numbers to run:
# "1" for sim, ..., "7" for stage2, "8" for ens_hopper. By default 1-7 are run.
requested_step=${4:-1234567}
requested() { [[ $requested_step =~ $1 ]]; }

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
script_dir="$MODULES/exafel_project/post-validate/general"
echo "Job name:        "$job
echo "Output root:     "$odir
echo "GPU settings:    "$GPU
echo "CPU settings:    "$CPU
echo "Number of shots: "$nshot
echo "w/ unrestrained: "$n_unrestrain

# times calibrated for 1 node per 1024 shots
if requested 1; then sbatch -J$job $GPU -t 40  -o${odir}/sim.out -e${odir}/sim.err ${script_dir}/general_sim.sh $length $nshot $detdist $pdb $odir ; fi
if requested 2; then sbatch -J$job $CPU -t 15  -o${odir}/idx.out -e${odir}/idx.err ${script_dir}/general_index.sh $dmin $spcgrp $ucell $odir ; fi
if requested 3; then sbatch -J$job $CPU -t 10  -o${odir}/mrg.out -e${odir}/mrg.err ${script_dir}/general_merge.sh $cov $pdb $dmin $odir ; fi
if requested 4; then sbatch -J$job $CPU -t 5   -o${odir}/spl.out -e${odir}/spl.err ${script_dir}/general_split.sh $odir ; fi
if requested 5; then sbatch -J$job $GPU -t 60  -o${odir}/st1.out -e${odir}/st1.err ${script_dir}/general_stage1_restraints_to_gt.sh $sigu $spcgrp $odir ${n_unrestrain} $nabc ; fi
if requested 6; then sbatch -J$job $GPU -t 15  -o${odir}/prd.out -e${odir}/prd.err ${script_dir}/general_predict.sh $dmin $spcgrp $ucell $odir ; fi
if requested 7; then sbatch -J$job $GPU -t 120 -o${odir}/st2.out -e${odir}/st2.err ${script_dir}/general_stage2.sh $dmin $odir ; fi
# optional ens.hopper:
if requested 8; then sbatch -J$job $GPU -t 121 -o${odir}/ens.out -e${odir}/ens.err ${script_dir}/general_ensHopper.sh $dmin $odir ; fi
