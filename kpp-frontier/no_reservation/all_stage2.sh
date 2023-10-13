#!/bin/bash
#SBATCH -N 5120            # Number of nodes
#SBATCH -J stage2          # job name
#SBATCH -A CHM137          # allocation
#SBATCH -p batch
#SBATCH -t 120
#SBATCH -o %j.out
#SBATCH -e %j.err
export SRUN="srun -N 256 -n 4096 -c2" # twenty sruns can run simultaneously in this batch job

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export SCRATCH_FOLDER=$SCRATCH/no_reservation/$SLURM_JOB_ID
mkdir -p $SCRATCH_FOLDER; cd $SCRATCH_FOLDER

export PERL_NDEV=8  # number GPU per node
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt

export CCTBX_DEVICE_PER_NODE=8
export N_START=0
export LOG_BY_RANK=1 # Use Aaron's rank logger
export RANK_PROFILE=0 # 0 or 1 Use cProfiler, default 1
export ADD_BACKGROUND_ALGORITHM=cuda
export DEVICES_PER_NODE=8
export MOS_DOM=25

export CCTBX_NO_UUID=1
export DIFFBRAGG_USE_KOKKOS=1
export CUDA_LAUNCH_BLOCKING=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=32
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export MPI4PY_RC_RECV_MPROBE='False'
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export CCTBX_GPUS_PER_NODE=8
export XFEL_CUSTOM_WORKER_PATH=$MODULES/psii_spread/merging/application # User must export $MODULES path

# copy program to nodes
echo "start cctbx transfer $(date)"
export CCTBX_ZIP_FILE=alcc-recipes3.tar.gz
sbcast $SCRATCH/$CCTBX_ZIP_FILE /tmp/$CCTBX_ZIP_FILE
srun -n $SLURM_NNODES -N $SLURM_NNODES tar -xf /tmp/$CCTBX_ZIP_FILE -C /tmp/
. /tmp/alcc-recipes/cctbx/activate.sh
echo "finish cctbx extraction $(date)"

# cry11ba datasets ----------------------------------------------------------

export tag=cry11ba
echo "
max_sigz = 4.
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 10
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
  skip_roi_with_negative_bg = True
}
space_group=P21212

sigmas {
  G = 1
  Fhkl = 1
}

refiner {
  refine_Fcell = [1]
  #refine_Nabc = [1]
  refine_spot_scale = [1]
  max_calls = [450]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 3
  num_devices = 4
  adu_per_photon = 1
  res_ranges='1.75-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

simulator {
  crystal.has_isotropic_ncells = False
  #structure_factors.mtz_name = merged/iobs_all.mtz
  structure_factors.mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  beam.size_mm = 0.001
  detector {
    force_zero_thickness = True
  }
}

logging {
  rank0_level = low normal *high
  logfiles = False # True for memory troubleshooting but consumes 3 seconds of wall time
}
" > stage_two_${tag}.phil

# run program for each ordered set of job IDs matching one crystal size
# each row is one job's index, merge, and predict job IDs, in that order
# rows are 16, 8, 4, 2, 1, and 0.5 micron crystal sizes, in that order
# (0.5 micron dataset is dropped for 5-srun batch job)
export job_ids_arr=(
1429675 1429811 1437715
1429676 1429812 1437713
1429680 1429813 1433651
1429681 1429814 1433652
#1429682 1429815 xxxxxxx # skip 1 micron size -- predict step not ready
1429809 1429819 1437694)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/cry11ba/${JOB_ID_MERGE}/out/cry11ba_500k_all.mtz
  export PANDA=$SCRATCH/cry11ba/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  export redirect1=" > ${tag}_job${job}.out 2> ${tag}_job${job}.err"
  export redirect2=" >> ${tag}_job${job}.out 2>> ${tag}_job${job}.err"
  export script=${tag}_job${job}.sh
  env > ${tag}_env${job}.out
  echo "#! /bin/bash
echo \"jobstart $tag job $job \$(date)\" $redirect1
pwd $redirect2
echo \"running stage 2 on 524k $tag images with command $SRUN\"
$SRUN simtbx.diffBragg.stage_two stage_two_${tag}.phil \
io.output_dir=${SLURM_JOB_ID}_${tag}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=$MTZ $redirect2
echo \"jobend \$(date)\" $redirect2
pwd $redirect2
" > $script
  chmod +x $script
  ./$script &
done
#wait

# cytochrome datasets --------------------------------------------------------

export tag=cyto
echo "
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 10
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
}
space_group=P6522

sigmas {
  G = 1
  Fhkl = 1
}

refiner {
  refine_Fcell = [1]
  #refine_Nabc = [1]
  refine_spot_scale = [1]
  max_calls = [450]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 3
  num_devices = 4
  adu_per_photon = 1
  res_ranges='1.5-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

simulator {
  crystal.has_isotropic_ncells = False
  #structure_factors.mtz_name = merged/iobs_all.mtz
  structure_factors.mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  beam.size_mm = 0.001
  detector {
    force_zero_thickness = True
  }
}

logging {
  rank0_level = low normal *high
  logfiles = False # True for memory troubleshooting but consumes 3 seconds of wall time
}
" > stage_two_${tag}.phil

# run program for each ordered set of job IDs matching one crystal size
# each row is one job's index, merge, and predict job IDs, in that order
# rows are 40, 25, 10, 5, and 2 micron crystal sizes, in that order
export job_ids_arr=(
1426077 1427767 1435064
1429648 1429661 1434948
1427782 1427786 1435065
1427783 1427787 1435069
1429649 1429662 1435711)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/cytochrome/${JOB_ID_MERGE}/out/ly99sim_all.mtz
  export PANDA=$SCRATCH/cytochrome/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  export redirect1=" > ${tag}_job${job}.out 2> ${tag}_job${job}.err"
  export redirect2=" >> ${tag}_job${job}.out 2>> ${tag}_job${job}.err"
  export script=${tag}_job${job}.sh
  env > ${tag}_env${job}.out
  echo "#! /bin/bash
echo \"jobstart $tag job $job \$(date)\" $redirect1
pwd $redirect2
echo \"running stage 2 on 524k $tag images with command $SRUN\"
$SRUN simtbx.diffBragg.stage_two stage_two_${tag}.phil \
io.output_dir=${SLURM_JOB_ID}_${tag}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=$MTZ $redirect2
echo \"jobend \$(date)\" $redirect2
pwd $redirect2
" > $script
  chmod +x $script
  ./$script &
done
#wait

# thermolysin datasets ------------------------------------------------------

export tag=thermo
echo "
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 15
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
}
space_group=P6122

sigmas {
  G = 1
  Fhkl = 1
}

refiner {
  refine_Fcell = [1]
  #refine_Nabc = [1]
  refine_spot_scale = [1]
  max_calls = [450]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 3
  num_devices = 8
  adu_per_photon = 1
  res_ranges='1.75-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

simulator {
  crystal.has_isotropic_ncells = False
  #structure_factors.mtz_name = merged/iobs_all.mtz
  structure_factors.mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  beam.size_mm = 0.001
  detector {
    force_zero_thickness = True
  }
}

logging {
  rank0_level = low normal *high
  logfiles = False
}
" > stage_two_${tag}.phil

# run program for each ordered set of job IDs matching one crystal size
# each row is one job's index, merge, and predict job IDs, in that order
# rows are 20, 10, 5, 2, 1, and 0.5 micron crystal sizes, in that order
# (0.5 micron size is dropped for 5-srun batch job)
export job_ids_arr=(
1433992 1435935 1444175
1430293 1435907 1444174
1431151 1435356 1444173
1431150 1450095 1452682
1431149 1434920 1443110)
#1432661 1434903 1437231)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/thermolysin/${JOB_ID_MERGE}/out/ly99sim_all.mtz
  export PANDA=$SCRATCH/thermolysin/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  export redirect1=" > ${tag}_job${job}.out 2> ${tag}_job${job}.err"
  export redirect2=" >> ${tag}_job${job}.out 2>> ${tag}_job${job}.err"
  export script=${tag}_job${job}.sh
  env > ${tag}_env${job}.out
  echo "#! /bin/bash
echo \"jobstart $tag job $job \$(date)\" $redirect1
pwd $redirect2
echo \"running stage 2 on 524k $tag images with command $SRUN\"
$SRUN simtbx.diffBragg.stage_two stage_two_${tag}.phil \
io.output_dir=${SLURM_JOB_ID}_${tag}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=$MTZ $redirect2
echo \"jobend \$(date)\" $redirect2
pwd $redirect2
" > $script
  chmod +x $script
  ./$script &
done
#wait

# lysozyme datasets ---------------------------------------------------------

export tag=yb_lyso
echo "
spectrum_from_imageset = True
downsamp_spec {
  skip = True
}
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 15
  fit_tilt = True
  fit_tilt_using_weights = False
  reject_edge_reflections = True
  pad_shoebox_for_background_estimation = 0
}
space_group=P43212

sigmas {
  G = 1
  Fhkl = 1
}

refiner {
  refine_Fcell = [1]
  #refine_Nabc = [1]
  refine_spot_scale = [1]
  max_calls = [450]
  ncells_mask = 000
  tradeps = 1e-20
  verbose = 0
  sigma_r = 3
  num_devices = 4
  adu_per_photon = 1
  res_ranges='1.75-999'
  stage_two.save_model_freq=None
  stage_two.save_Z_freq=None
}

simulator {
  crystal.has_isotropic_ncells = False
  #structure_factors.mtz_name = merged/iobs_all.mtz
  structure_factors.mtz_column = 'Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)'
  beam.size_mm = 0.001
  detector {
    force_zero_thickness = True
  }
}

logging {
  rank0_level = low normal *high
  logfiles = False # True for memory troubleshooting but consumes 3 seconds of wall time
}
" > stage_two_${tag}.phil

# run program for each ordered set of job IDs matching one crystal size
# each row is one job's index, merge, and predict job IDs, in that order
# rows are 2, 1, 0.5, 0.25, and 0.125 micron crystal sizes, in that order
export job_ids_arr=(
1427014 1427835 1428320
1427017 1427900 1428322
1411658 1427901 1428333
1427020 1427902 1428365
1427035 1427903 1428853)

for job in {0..4}; do
  export JOB_ID_INDEX=${job_ids_arr[job*3]} # not used
  export JOB_ID_MERGE=${job_ids_arr[job*3+1]}
  export JOB_ID_PREDICT=${job_ids_arr[job*3+2]}
  export MTZ=${SCRATCH}/yb_lyso/${JOB_ID_MERGE}/out/yb_lyso_500k_all.mtz
  export PANDA=$SCRATCH/yb_lyso/${JOB_ID_PREDICT}/predict/preds_for_hopper.pkl
  export redirect1=" > ${tag}_job${job}.out 2> ${tag}_job${job}.err"
  export redirect2=" >> ${tag}_job${job}.out 2>> ${tag}_job${job}.err"
  export script=${tag}_job${job}.sh
  env > ${tag}_env${job}.out
  echo "#! /bin/bash
echo \"jobstart $tag job $job \$(date)\" $redirect1
pwd $redirect2
echo \"running stage 2 on 524k $tag images with command $SRUN\"
$SRUN simtbx.diffBragg.stage_two stage_two_${tag}.phil \
io.output_dir=${SLURM_JOB_ID}_${tag}_job${job} \
pandas_table=$PANDA num_devices=$PERL_NDEV \
simulator.structure_factors.mtz_name=$MTZ $redirect2
echo \"jobend \$(date)\" $redirect2
pwd $redirect2
" > $script
  chmod +x $script
  ./$script &
done

# wait for all srun jobs to complete
wait

