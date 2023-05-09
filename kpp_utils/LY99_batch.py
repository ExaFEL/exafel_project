from __future__ import division, print_function
from datetime import datetime
import io
from time import time
import os
import sys
start_elapse = time()

from scitbx.matrix import sqr
import libtbx.load_env  # possibly implicit
from omptbx import omp_get_num_procs

# %%% boilerplate specialize to packaged big data %%%

from LS49.sim import step4_pad
from LS49.spectra import generate_spectra
from LS49 import ls49_big_data, legacy_random_orientations
step4_pad.big_data = ls49_big_data
generate_spectra.big_data = ls49_big_data
from simtbx import get_exascale
# %%%%%%

# Develop procedure for MPI control

# later, spectra to spectra iter
# data, why are we reading those files in all ranks?
# sfall_main not used?
# evaluate air + water as a singleton

from exafel_project.kpp_utils.phil import parse_input
from exafel_project.kpp_utils.ferredoxin import basic_detector_rayonix
from exafel_project.kpp_utils.amplitudes_spread_ferredoxin import ferredoxin
from exafel_project.kpp_utils.psii_utils import psii_amplitudes_spread


def tst_one(image,spectra,crystal,random_orientation,sfall_channels,gpu_channels_singleton,rank,params,**kwargs):
  iterator = spectra.generate_recast_renormalized_image(image=image%100000,energy=params.beam.mean_wavelength,
  total_flux=params.beam.total_flux)
  quick = False
  prefix_root = "LY99_batch_%06d" if quick else "LY99_MPIbatch_%06d"
  file_prefix = prefix_root%image
  rand_ori = sqr(random_orientation)
  from exafel_project.kpp_utils.ferredoxin import run_sim2smv
  run_sim2smv(prefix = file_prefix,
              crystal = crystal,
              spectra=iterator,rotation=rand_ori,quick=quick,rank=rank,
              gpu_channels_singleton=gpu_channels_singleton,
              sfall_channels=sfall_channels,params=params,**kwargs)


def run_LY99_batch(test_without_mpi=False):
  params,options = parse_input()
  log_by_rank = bool(int(os.environ.get("LOG_BY_RANK",0)))
  rank_profile = bool(int(os.environ.get("RANK_PROFILE",1)))
  if rank_profile:
    import cProfile
    pr = cProfile.Profile()
    pr.enable()

  if test_without_mpi:
    from LS49.adse13_196.mock_mpi import mpiEmulator
    MPI = mpiEmulator()
  else:
    from libtbx.mpi4py import MPI

  comm = MPI.COMM_WORLD
  rank = comm.Get_rank()
  size = comm.Get_size()
  import omptbx
  workaround_nt = int(os.environ.get("OMP_NUM_THREADS",1))
  omptbx.omp_set_num_threads(workaround_nt)
  N_total = int(os.environ["N_SIM"]) # number of items to simulate
  N_stride = size # total number of worker tasks
  print("hello from rank %d of %d"%(rank,size),"with omp_threads=",omp_get_num_procs())
  start_comp = time()

  # now inside the Python imports, begin energy channel calculation
  sfall_channels_d = {'ferredoxin': ferredoxin, 'PSII': psii_amplitudes_spread}
  sfall_channels = sfall_channels_d[params.crystal.structure](comm)
  print(rank, time(), "finished with the calculation of channels, now construct single broadcast")

  if rank == 0:
    print("Rank 0 time", datetime.now())
    from LS49.spectra.generate_spectra import spectra_simulation
    from LS49.sim.step4_pad import microcrystal
    print("hello2 from rank %d of %d"%(rank,size))
    SS = spectra_simulation()
    C = microcrystal(Deff_A = 4000, length_um = 4., beam_diameter_um = 1.0) # assume smaller than 10 um crystals
    random_orientations = legacy_random_orientations(N_total)
    transmitted_info = dict(spectra = SS,
                            crystal = C,
                            sfall_info = sfall_channels,
                            random_orientations = random_orientations)
  else:
    transmitted_info = None
  transmitted_info = comm.bcast(transmitted_info, root = 0)
  comm.barrier()
  parcels = list(range(rank,N_total,N_stride))

  print(rank, time(), "finished with single broadcast, now set up the rank logger")
  if log_by_rank:
    expand_dir = os.path.expandvars(params.logger.outdir)
    log_path = os.path.join(expand_dir,"rank_%d.log"%rank)
    error_path = os.path.join(expand_dir,"rank_%d.err"%rank)
    #print("Rank %d redirecting stdout/stderr to"%rank, log_path, error_path)
    sys.stdout = io.TextIOWrapper(open(log_path,'ab', 0), write_through=True)
    sys.sntderr = io.TextIOWrapper(open(error_path,'ab', 0), write_through=True)

  print(rank, time(), "finished with the rank logger, now construct the GPU cache container")
  gpu_instance = get_exascale("gpu_instance", params.context)
  gpu_energy_channels = get_exascale("gpu_energy_channels", params.context)

  gpu_run = gpu_instance( deviceId = rank % int(os.environ.get("DEVICES_PER_NODE",1)) )
  gpu_channels_singleton = gpu_energy_channels (
    deviceId = gpu_run.get_deviceID())
    # singleton will instantiate, regardless of gpu, device count, or exascale API

  comm.barrier()

  kwargs = {}
  if params.output.format == "h5":
    from simtbx.nanoBragg import nexus_factory
    fileout_name="image_rank_%05d.h5"%rank
    kwargs["writer"] = nexus_factory(fileout_name) # break encapsulation, use kwargs to push writer to inner loop
    if params.detector.tiles == "single":
      DETECTOR = basic_detector_rayonix()
    else:
      from exafel_project.kpp_utils.multipanel import specific_expt, run_sim2h5
      specific = specific_expt(params)
      DETECTOR = specific.detector
    kwargs["writer"].construct_detector(DETECTOR)


  for idx in parcels:
    cache_time = time()
    print("idx------start-------->",idx,"rank",rank,time())
    # if rank==0: os.system("nvidia-smi")
    if params.detector.tiles == "single":
      tst_one(image=idx,spectra=transmitted_info["spectra"],
        crystal=transmitted_info["crystal"],
        random_orientation=transmitted_info["random_orientations"][idx],
        sfall_channels=transmitted_info["sfall_info"], gpu_channels_singleton=gpu_channels_singleton,
        rank=rank,params=params,**kwargs
      )
    else:
      iterator = transmitted_info["spectra"].generate_recast_renormalized_image(
        image=idx%100000,energy=params.beam.mean_wavelength,total_flux=params.beam.total_flux)
      run_sim2h5(spectra = iterator,
        reference = specific,
        crystal = transmitted_info["crystal"],
        rotation = sqr(transmitted_info["random_orientations"][idx]),
        rank = rank,
        gpu_channels_singleton=gpu_channels_singleton,
        sfall_channels=transmitted_info["sfall_info"],
        params=params,**kwargs
      )
    print("idx------finis-------->",idx,"rank",rank,time(),"elapsed",time()-cache_time)
  comm.barrier()
  del gpu_channels_singleton
  # avoid Kokkos allocation "device_Fhkl" being deallocated after Kokkos::finalize was called
  print("Overall rank",rank,"at",datetime.now(),"seconds elapsed after srun startup %.3f"%(time()-start_elapse))
  print("Overall rank",rank,"at",datetime.now(),"seconds elapsed after Python imports %.3f"%(time()-start_comp))
  if rank_profile:
    pr.disable()
    pr.dump_stats("cpu_%d.prof"%rank)


if __name__=="__main__":
  run_LY99_batch()
