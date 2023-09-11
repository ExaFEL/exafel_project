#!/bin/bash -l
#SBATCH -N 512
#SBATCH -J index
#SBATCH -A CHM137
#SBATCH -p batch
#SBATCH -t 20
#SBATCH -o %j.out
#SBATCH -e %j.err
export NTASKS_PER_NODE=56
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
echo "indexing on $STEP_NNODES nodes with $SRUN"

export JOB_ID_SIM=$1

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export H5_SIM_PATH=$SCRATCH/thermolysin/$JOB_ID_SIM

export NUMEXPR_MAX_THREADS=56
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'

export TRIAL=tdata
export OUT_DIR=.
export DIALS_OUTPUT=.

mkdir -p ${OUT_DIR}/${TRIAL}/out
mkdir -p ${OUT_DIR}/${TRIAL}/tmp
echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes2.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"
env > env.out

echo "
output {
  composite_output = True
  integration_pickle=None
  logging_dir=. # demangle by rank
}
dispatch {
  index=True
  refine=True
  integrate=True
}
mp.method = mpi
spotfinder {
  lookup {
    #mask = '/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask'
  }
  threshold {
    dispersion {
      gain = 1.0 # for nanoBragg sim
      sigma_background=2
      sigma_strong=2
      global_threshold=10
      kernel_size=6 6
    }
  }
  filter.min_spot_size=3
  filter.d_min=1.9
}
indexing {
  stills.refine_candidates_with_known_symmetry=True
  known_symmetry {
    space_group = 'P6122'
    unit_cell = 93.0407 93.0407 130.41 90 90 120
  }
}
integration {
  background.simple.outlier.plane.n_sigma=10
  #debug.output=True
  #debug.separate_files=False
  lookup {
    #mask = '/global/cfs/cdirs/m3562/dwpaley/masks/4more.mask'
  }
  summation {
    detector_gain = 1.0 # for nanoBragg sim
  }
}
profile.gaussian_rs.centroid_definition=com

indexing.stills.refine_all_candidates=False
refinement.reflections.outlier.algorithm=None
dispatch.refine=True
indexing.stills.nv_reject_outliers=False
">index.phil

echo "jobstart $(date)";pwd
$SRUN dials.stills_process index.phil input.glob=$H5_SIM_PATH/image_rank_*.h5
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi

echo "dispatch.step_list=input tdata
input.path=${DIALS_OUTPUT}
input.experiments_suffix=_integrated.expt
input.reflections_suffix=_integrated.refl
input.parallel_file_load.method=uniform
tdata.output_path=${TRIAL}_cells
output.prefix=${TRIAL}
output.output_dir=${OUT_DIR}/${TRIAL}/out
output.tmp_dir=${OUT_DIR}/${TRIAL}/tmp
output.do_timing=True
output.log_level=0
" > tdata.phil

echo "jobstart $(date)";pwd
$SRUN cctbx.xfel.merge tdata.phil
echo "jobend $(date)";pwd
if [ "$(cat ../${SLURM_JOB_ID}.err)" != "" ]; then exit; fi
