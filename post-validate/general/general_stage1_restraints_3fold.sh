#!/bin/bash

# work flow is
#  1- look at stills process crystals to estimate Nabc (from ML_domain_size_ang)
#  2- run stage1 with estimated Nabc and init.eta=.1 on a subset of the shots
#  3- estimate restraints terms
#  4- re-run stage 1 on all shows using restraints

SRUN="srun -c2"
export SIGU=$1
export SPCGRP=$2
H5_SIM_PATH=$3
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
N_FIRST_PASS=$4 # number of shots to process in order to gauge restraints
export INDEX_PATH=${H5_SIM_PATH}/index # stills process output folder
export MTZ_PATH=${H5_SIM_PATH}/merge/out/ly99sim_all.mtz  # xfel.merge output file
export SPEC_PATH=${H5_SIM_PATH}/integ_exp_ref.txt  # diffBragg.make_input_file output file
export SCRATCH_FOLDER=${H5_SIM_PATH}/stage1
mkdir -p "$SCRATCH_FOLDER"; cd "$SCRATCH_FOLDER" || exit

export DEVICES_PER_NODE=4

export DIFFBRAGG_USE_KOKKOS=1
export HIP_LAUNCH_BLOCKING=1
export NUMEXPR_MAX_THREADS=128
export SLURM_CPU_BIND=cores # critical to force ranks onto different cores. verify with ps -o psr <pid>
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export SIT_PSDM_DATA=/global/cfs/cdirs/lcls/psdm-sauter
export MPI4PY_RC_RECV_MPROBE='False'
env > env.out
OUTDIR=unrestrained

echo "
symmetrize_Flatt = True
record_device_timings = True # only applies to rank0
lbfgs_maxiter = 1500
spectrum_from_imageset = True
method = 'L-BFGS-B'
debug_mode = False
roi {
  shoebox_size = 10
  fit_tilt = True
  reject_edge_reflections = False
  reject_roi_with_hotpix = False
  pad_shoebox_for_background_estimation = 0
  fit_tilt_using_weights = False
  mask_outside_trusted_range = True
}

fix {
  eta_abc = False
  detz_shift = True
  ucell=False
  Nabc=False
  G=False
  RotXYZ=False
}
use_restraints = False
sigmas {
  ucell = ${SIGU}
  RotXYZ = 0.001 0.001 0.001
  G = 1
  Nabc = 1 1 1
  eta_abc = [1,1,1]
}

init {
  G = 1e4
}

refiner {
  num_devices=${DEVICES_PER_NODE}
  verbose = 0
  sigma_r = 3
  adu_per_photon = 1
}

simulator {
  spectrum.stride = 4
  oversample = 1
  crystal {
    has_isotropic_ncells = False
    has_isotropic_mosaicity = True
    num_mosaicity_samples = 26
  }
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
  RotXYZ = -3.14 -3.14 -3.14
  G = 1e2
}
maxs {
  detz_shift = 1.5
  Nabc = 1600 1600 1600
  RotXYZ = 3.14 3.14 3.14
  G = 1e6
  eta_abc = 360 360 360
}
ucell_edge_perc = 15
ucell_ang_abs = 1
space_group =${SPCGRP}
logging {
  rank0_level = low normal *high
  parameters = True
}
downsamp_spec {
  skip = True
}
" > stage1.phil

echo "jobstart $(date)";pwd

# read the stills process folder for domain size estimates, and append them to stage1.phil 
$SRUN diffBragg.estimate_Ncells_Eta $INDEX_PATH --updatePhil stage1.phil
sleep 10
# first run stage 1 to estimate parameter trends 
$SRUN hopper stage1.phil structure_factors.mtz_name="$MTZ_PATH" exp_ref_spec_file="$SPEC_PATH" max_process=${N_FIRST_PASS} outdir=$OUTDIR
sleep 11
# use the results from the first stage 1 pass to estimate better initial conditions and averages 
NEW_PHIL=stage1_updated.phil
diffBragg.update_stage1_phil $OUTDIR $NEW_PHIL 
$SRUN hopper $NEW_PHIL max_process=-1 outdir=. filter_during_refinement.enable=True filter_after_refinement.enable=True

echo "jobend $(date)";pwd
