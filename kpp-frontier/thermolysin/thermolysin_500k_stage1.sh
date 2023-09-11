#!/bin/bash -l
#SBATCH -N 512
#SBATCH -J stage1
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 60
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS_PER_NODE=32
export NTASKS=$((SLURM_JOB_NUM_NODES * NTASKS_PER_NODE))
export NODELIST=`scontrol show hostnames $SLURM_NODELIST`

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/thermolysin/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER
echo "#! /bin/bash
echo \"reporting from task \$SLURM_LOCALID of \$SLURM_NTASKS on node \$SLURM_NODEID of \$SLURM_NNODES running on \$SLURMD_NODENAME\"
" > check_nodes.sh
chmod +x check_nodes.sh

srun -N $SLURM_NNODES -n${NTASKS} -c1 -t2 ./check_nodes.sh > node_report.out

if [ -f "nodelist_ok" ]; then rm nodelist_ok; fi
if [ -f "nodelist_exclude" ]; then rm nodelist_exclude; fi
for nodename in $NODELIST; do
        export count=`grep "running on $nodename" node_report.out | wc -l`
        if [ ! "$count" == "$NTASKS_PER_NODE" ]
                then
                        echo "exclude node $nodename"
                        echo -n "$nodename," >> nodelist_exclude
                else
                        echo "node $nodename OK"
                        echo -n "$nodename," >> nodelist_ok
        fi
done

#export SLURM_STEP_NODELIST=$(cat nodelist_ok)
export STEP_NNODES=`sed "s:,: :g" nodelist_ok | wc -w`
export NTASKS=$((STEP_NNODES * NTASKS_PER_NODE))
if [ -f "nodelist_exclude" ]; then
        export EXCLUDE="--exclude=$(cat nodelist_exclude)"
fi

export SRUN="srun -N$STEP_NNODES -n$NTASKS -c1 $EXCLUDE --cpu-bind=cores"
echo "running diffBragg stage 1 on $STEP_NNODES nodes with $SRUN"

export JOB_ID_SPLIT=$1
export JOB_ID_MERGE=$2

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export MTZ=$SCRATCH/thermolysin/${JOB_ID_MERGE}/out/ly99sim_all.mtz
export SPEC=$SCRATCH/thermolysin/${JOB_ID_SPLIT}_integ_exp_ref.txt

export CCTBX_DEVICE_PER_NODE=8
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export DEVICES_PER_NODE=8

export DIFFBRAGG_USE_KOKKOS=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=56
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'
export CCTBX_GPUS_PER_NODE=8

env > env.out

echo "
spectrum_from_imageset = True
method = 'L-BFGS-B'
outdir = 'stage1'
debug_mode = False
roi {
  shoebox_size = 15
  fit_tilt = True
  reject_edge_reflections = False
  reject_roi_with_hotpix = False
  pad_shoebox_for_background_estimation = 0
  fit_tilt_using_weights = False
  mask_outside_trusted_range = True
}

fix {
  detz_shift = True
  ucell=False
  Nabc=False
  G=False
  RotXYZ=False
}

sigmas {
  ucell = .1 .1
  RotXYZ = 0.01 0.01 0.01
  G = 1
  Nabc = 1 1 1
}

init {
  Nabc = 52 52 52
  G = 1e5
}

refiner {
  num_devices=4
  verbose = 0
  sigma_r = 3
  adu_per_photon = 1
  #reference_geom = '${MODULES}/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt'
}

simulator {
  oversample = 1
  crystal.has_isotropic_ncells = False
  structure_factors {
    mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  }
  beam {
    size_mm = 0.001
  }
  detector {
    force_zero_thickness = True
  }
}

mins {
  detz_shift = -1.5
  RotXYZ = -15 -15 -15
}
maxs {
  detz_shift = 1.5
  Nabc = 1600 1600 1600
  RotXYZ = 15 15 15
}
ucell_edge_perc = 15
ucell_ang_abs = 1
space_group = P6122
use_restraints = False
logging {
  rank0_level = low normal *high
}
downsamp_spec {
  skip = True
}
" > stage1.phil

echo "jobstart $(date)";pwd
$SRUN hopper stage1.phil structure_factors.mtz_name=$MTZ exp_ref_spec_file=$SPEC
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
