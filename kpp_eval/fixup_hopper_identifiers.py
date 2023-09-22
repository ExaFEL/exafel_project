# This script utilised a fixed mpi4py structure and needs to be run
# using the same number of cores as used by the stage 1 hopper, i.e. usually:
# `srun -n 256 -c 4 -N 4 libtbx.python fixup_hopper_identifiers.py`

from glob import glob
from pathlib import Path

from dials.array_family import flex
from dxtbx.model import ExperimentList
from xfel.merging.application.input.file_lister import StemLocator

from mpi4py import MPI
from orderedset import OrderedSet

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~ VARIABLES TO DECLARE ~~~~~~~~~~~~~~~~~~~~~~~~~~ #
HOPPER_DIR = '/pscratch/sd/v/vidyagan/ferredoxin_sim/10780908/hopper_stage_one'
OUTPUT_DIR = '/pscratch/sd/d/dtchon/fixup_hopper_identifiers/'
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ END OF VARIABLES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


expt_glob = HOPPER_DIR + '/expers/rank' + str(rank) + '/*.expt'
refl_glob = HOPPER_DIR + '/refls/rank' + str(rank) + '/*.refl'
output_dir = Path(OUTPUT_DIR, 'expers/rank' + str(rank))

expt_stem_locator = StemLocator()
refl_stem_locator = StemLocator()


def stem_of(path: str) -> str:
  return Path(path).stem


def main() -> None:
  for expt_path in glob(expt_glob):
    expt_stem_locator[stem_of(expt_path)] = expt_path
  for refl_path in glob(refl_glob):
    refl_stem_locator[stem_of(refl_path)] = refl_path
  common_stems = OrderedSet(expt_stem_locator) & OrderedSet(refl_stem_locator)
  print(f'{rank=}', len(common_stems))
  for stem in common_stems:
    expts = ExperimentList.from_file(expt_stem_locator[stem], check_format=False)
    refls = flex.reflection_table.from_file(refl_stem_locator[stem])
    assert not expts[0].identifier
    if len(refls.experiment_identifiers()) > 0:
      expts[0].identifier = refls.experiment_identifiers()[0]
      assert expts[0].identifier
    expts.as_file(Path(output_dir, stem + '.expt'))


if __name__ == '__main__':
  main()
