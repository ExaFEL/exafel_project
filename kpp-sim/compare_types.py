from __future__ import division
from dxtbx.model.experiment_list import (
    Experiment,
    ExperimentList,
    ExperimentListFactory,
)
from dxtbx.imageset import ImageSetFactory
print ("done importing modules")
def paths_smv():
  for idx in range(98):
    # NOTE Hardcoded file path needs to be changed for your script
    yield "/pscratch/sd/n/nksauter/ferredoxin_sim/6316618/LY99_MPIbatch_%06d.img.gz"%idx

def paths_h5():
  for idx in range(1):
    # NOTE Hardcoded file path needs to be changed for your script
    #yield "/pscratch/sd/n/nksauter/ferredoxin_sim/6346286/image_rank_%05d.h5"%idx
    yield "/pscratch/sd/n/nksauter/ferredoxin_sim/6677492/image_rank_%05d.h5"%idx

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
            yield imageset.get_raw_data(0)

if __name__=="__main__":
  from scitbx.array_family import flex
  # Run both types of data.
  for sm, hn in zip( run(paths_smv()), run(paths_h5())):
    smarray = sm[0]
    print("SMV", flex.min(smarray), flex.max(smarray), flex.mean(smarray.as_double()), flex.median(smarray.as_double().as_1d()))
    hnarray = hn[0]
    print("H5 ", flex.min(hnarray), flex.max(hnarray), flex.mean(hnarray.as_double()), flex.median(hnarray.as_double().as_1d()))
    diff = hnarray - smarray
    print("dif", flex.min(diff), flex.max(diff), flex.mean(diff.as_double()) )

    print(list(diff[1000:2000]))
    diff = flex.log((diff+1).as_double())
    print(flex.min(diff), flex.max(diff))
    from matplotlib import pyplot as plt
    plt.imshow(diff.as_numpy_array(), norm="linear")
    plt.show()
    break # only compare first diffraction pattern, the others are not mutually registered
