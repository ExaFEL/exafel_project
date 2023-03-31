from __future__ import division
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

def paths_smv():
  for idx in range(rank,100000,size):
    # NOTE Hardcoded file path needs to be changed for your script
    yield "/pscratch/sd/n/nksauter/ferredoxin_sim/6316618/LY99_MPIbatch_%06d.img.gz"%idx

def paths_h5():
  for idx in range(rank,1024,size):
    # NOTE Hardcoded file path needs to be changed for your script
    yield "/pscratch/sd/n/nksauter/ferredoxin_sim/6346286/image_rank_%05d.h5"%idx

def run(iterator):
  for path in iterator:
    print(path)
    experiments = ExperimentListFactory.from_filenames([path], load_models=False)
    for iexp,experiment in enumerate(experiments):
        print("Iteration",iexp)
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

            print(imageset.get_spectrum(0))
            print(imageset.get_raw_data(0))

if __name__=="__main__":
  # Run both types of data.
  import datetime
  if rank == 0:  print("Rank 0 time", datetime.datetime.now())

  run(paths_smv())
  comm.barrier()
  if rank == 0:  print("Rank 0 time", datetime.datetime.now())

  run(paths_h5())
  comm.barrier()
  if rank == 0:  print("Rank 0 time", datetime.datetime.now())
