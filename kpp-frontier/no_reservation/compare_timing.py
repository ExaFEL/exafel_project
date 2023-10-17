from __future__ import division
import socket

from dxtbx.model.experiment_list import (
    Experiment,
    ExperimentList,
    ExperimentListFactory,
)
from dxtbx.imageset import ImageSetFactory
if False:
    from LS49.adse13_196.mock_mpi import mpiEmulator
    MPI = mpiEmulator()
else:
    from libtbx.mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

def get_memory_usage():
  '''Return memory used by the process in MB'''
  import resource
  import platform
  # getrusage returns kb on linux, bytes on mac
  units_per_mb = 1024
  if platform.system() == "Darwin":
    units_per_mb = 1024*1024
  return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / units_per_mb

def _mem_usage(msg="Memory usage"):
        memMB = get_memory_usage()
        host = socket.gethostname()
        return "%s: %f GB on node %s" % (msg, memMB / 1024, host)

RANKS_PER_NODE = 8

def paths_h5():
  protein_nfiles = [8192, 8192, None, 2048]
  thermolysin_breakout = [28672, 7168, 7168, 7168, 28672]
  # cry11ba, 8192 H5 files, each 64 experiments; jobid for sim 16 8 4 2 0.5
  cry11ba_dirs = ['14887696','1429652','1429653','1429654','1429803']
  # cytochrome, 8192 H5 files, each 64 experiments; jobid for sim 40 25 20 5 2
  cyto_dirs = ['1425204','1429604','1427774','1427775','1429605']
  # thermolysin, 8192 H5 files, each 64 experiments; jobid for sim 20 10 5 2 1
  thermo_dirs = ['1430840','1429926','1430074','1430073','1430847']
  # yb_lyso, 8192 H5 files, each 64 experiments; jobid for sim 2, 1, .5, .25, .125
  yb_lyso_dirs = ['1426601','1426602','1411139','1426603','1426604']
  protein_dirs = [cry11ba_dirs, cyto_dirs, thermo_dirs, yb_lyso_dirs]
  """ # example set of raw data files
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00000.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00001.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00002.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00003.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00004.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00005.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00006.h5"
  yield "/lustre/orion/chm137/proj-shared/cctbx/cry11ba/1429803/image_rank_00007.h5"
  """
  # all data, 5120 nodes x 4 ranks = 20480 ranks
  # just cry11, 1280 nodes, 5120 ranks
  # just 1 crystal, 256 nodes, 1024 ranks

  expected_size = 5120 * RANKS_PER_NODE
  ranks_per_protein = expected_size // 4
  ranks_per_tranche = expected_size // 20
  assert size <= expected_size
  n_protein = rank // ranks_per_protein # identify which protein
  prodir = ['cry11ba','cytochrome','thermolysin','yb_lyso'][n_protein]
  n_cryst = (rank - n_protein * ranks_per_protein) // ranks_per_tranche
  if n_protein==2: # thermolysin, special case
    n_files = thermolysin_breakout[n_cryst]
  else:
    n_files = protein_nfiles[n_protein]
  crystdir = protein_dirs[n_protein][n_cryst]
  files_per_rank = n_files // ranks_per_tranche
  assert files_per_rank > 0
  n_rank_within_tranche = rank - (n_protein * ranks_per_protein) - (n_cryst * ranks_per_tranche)
  for idx in range(n_rank_within_tranche*files_per_rank, (1+n_rank_within_tranche)*files_per_rank):
    # NOTE Hardcoded file path needs to be changed for your script
    yield "/lustre/orion/chm137/proj-shared/cctbx/%s/%s/image_rank_%05d.h5"%(prodir,crystdir,idx)

def run(iterator):
  collect_images = []
  for path in iterator:
    try:
      experiments = ExperimentListFactory.from_filenames([path], load_models=False)
    except OSError as e:
      print ("Corrupt",e); break
    print("rank",rank,path, len(experiments))
    for iexp,experiment in enumerate(experiments):
        # Convert from ImageSequence to ImageSet, if needed
        imageset = ImageSetFactory.imageset_from_anyset(experiment.imageset)
        for i in range(len(imageset)):
            expt = Experiment(
                imageset=imageset[i : i + 1],
                detector=experiment.detector,
                beam=experiment.beam,
                scan=experiment.scan,
                goniometer=experiment.goniometer,
                crystal=experiment.crystal,
            )
            # Not sure if this is needed
            expt.load_models()

            imageset.get_spectrum(0)
            try:
              collect_images.append(imageset.get_raw_data(0))
            except OSError as e:
              print ("Caught",e); break
  # some ground truthing
  # might have to pass if len(collect_images)==0
  if len(collect_images)==0:
    print("No images rank",rank)
    return
  # some assertion of length of collect images
  # assert 504 <= len(collect_images) <= 532 # Nominally 512 (20480 ranks, 10**7 images) but varies for thermolysin
  #print("N_images",len(collect_images))
  assert len(collect_images[0]) == 256 # each raw image is a tuple of 256 Jungfrau panels
  assert collect_images[0][0].focus() == (254,254) # each panel is 256x256 pixels
  # each panel array is int32, therefore total memory should be
  gt_mem_MB = 4 * 254 * 254 * 256 * len(collect_images) / 1024 / 1024 # in MB
  mem_use_MB = get_memory_usage()
  assert gt_mem_MB < mem_use_MB < 1.2 * gt_mem_MB

if __name__=="__main__":
  # Run both types of data.
  import datetime
  if rank == 0:  print("Rank 0 time",  datetime.datetime.now(),"with proc memory: %s"%(_mem_usage()))

  run(paths_h5())
  comm.barrier()
  if True or rank == 0:  print("Rank 0F time", datetime.datetime.now(),"with proc memory: %s"%(_mem_usage()))
