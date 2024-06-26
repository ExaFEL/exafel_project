"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz and plot
the evolution of Pearson's R or CC of F or anom as a function of stage2 step.
"""
from enum import Enum
import glob
import os
import re
from typing import Callable, List, Sequence, Tuple

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from dials.array_family import flex
from cctbx import miller, crystal
import iotbx.mtz
import iotbx.pdb
from libtbx import Auto
from libtbx.utils import Sorry
from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb
from iotbx.reflection_file_reader import any_reflection_file

from exafel_project.kpp_eval.phil import parse_phil
from exafel_project.kpp_eval.util import set_default_return
from exafel_project.kpp_eval.evaluate_cc12 import CrossCorrelationSums


phil_scope_str = """
figprefix = ""
  .type = str
  .help = A prefix prepended to the name of the saved figure
stride = 1
  .type = int
  .help = skip this many iterations between plot points
all_evaluations = False
  .type = bool
  .help = If true, use files from all target evaluations. Otherwise use only iterations
pdb = None
  .type = str
  .help = Path to the pdb file to be analyzed. If None, 1m2a.pdb will be used.
mtz = None
  .type = str
  .help = Path to conventionally merged mtz file. If None,
  .help = use $SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz
stage2 = None
  .type = str
  .help = Directory with stage 2 results. If None,
  .help = use $WORK/exafel_output/$JOB_ID_STAGE2
is_ens_hopper = False
  .type = bool
  .help = Whether the stage2 folder is from ens.hopper, or the original stage2_refiner (default)
stat = *PearsonR_F PearsonR_anom cc_F cc_anom Rwork_F Rwork_anom significance_F significance_anom
  .type = choice(multi=False)
  .help = The type of statistic to be calculated
d_min = 1.9
  .type = float
  .help = Lower bound of data resolution to be investigated, in Angstrom
d_max = 9999.
  .type = float
  .help = Upper bound of data resolution to be investigated
wavelength = 1.3
  .type = float
  .help = Radiation wavelength used to generate ground-truth data, in Angstrom
n_bins = 1
  .type = int
  .help = Data will be divided into `n_bins` resolution ranges for evaluation
scatter_ranges = None
  .type = str
  .help = DiffBragg step ranges (in Python convention) to plot ground truth vs
  .help = refined data scatter for, f.e. "0:8:2,10" for steps 0, 2, 4, 6 & 10.
  .help = DIALS merging results can be plotted using step value of -1.
show = True
  .type = bool
  .help = Display final figure in an interactive window
save_mtz = none *missing all
  .type = choice
  .help = Which npz should be saved as mtz: none, missing (default), or all
  .help = (overwrites existing). Ignored if `is_ens_hopper = True`.
legend = *corner none top
  .type = choice
  .help = Where, and if, the legend should be placed on the final plot.
"""


bin_colors = []  # global list of colors used for plotting bins, filled later

def natural_sort(s, filter=re.compile('([0-9]+)')):
  return [int(text) if text.isdigit() else text.lower() for text in filter.split(s)]


@set_default_return('$MODULES/ls49_big_data/1m2a.pdb')
def get_pdb_path(params_) -> str:
  return params_.pdb


@set_default_return('$SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz')
def get_mtz_path(params_) -> str:
  return params_.mtz


@set_default_return('$WORK/exafel_output/$JOB_ID_STAGE2')
def get_stage2_path(params_) -> str:
  return params_.stage2


def expand_integer_ranges(ranges_str: str) -> List[int]:
  """Convert string of int ranges (e.g. "1:4,6") into list ([1, 2, 3, 6])"""
  indices = []
  if ranges_str:
    for range_str in ranges_str.split(','):
      range_descriptors = [int(v) for v in range_str.split(':')]
      if len(range_descriptors) == 1:
        indices.append(int(range_descriptors[0]))
      elif len(range_descriptors) in {2, 3}:
        indices.extend(list(range(*range_descriptors)))
      else:
        raise IndexError(f'Unknown range string format: "{range_str}"')
  return indices


def read_npz(npz_path: str,
             f_asu_map: dict,
             symmetry: 'crystal.symmetry',
             save_mtz: str,  # see help string for phil parameter `save_mtz`
             ) -> miller.array:
  """Read Miller array from .npz and f_asu_map, optionally save it as mtz"""
  f_values = np.load(npz_path)['fvals']
  miller_idx = flex.miller_index([f_asu_map[i] for i in range(len(f_values))])
  miller_set = miller.set(symmetry, miller_idx, True)
  miller_data = flex.double(f_values)
  ma = miller.array(miller_set, miller_data)
  ma = ma.set_observation_type_xray_amplitude()
  mtz_path = os.path.splitext(npz_path)[0] + '.mtz'
  if save_mtz == 'all' or \
    (save_mtz == 'missing' and not os.path.isfile(mtz_path)):
    ma.as_mtz_dataset(column_root_label='F').mtz_object().write(mtz_path)
  return ma


def bin_label_from(bin_range: Tuple[float, float]) -> str:
  return '-'.join(['{:.3f}'.format(m if m > 0 else np.nan) for m in bin_range])


def calc_pearson_r(ma1: miller.array, ma2: miller.array) -> float:
  return pearsonr(ma1.data(), ma2.data())[0]


def calc_cc_parameter(ma1: miller.array, ma2: miller.array) -> float:
  return CrossCorrelationSums.from_xy(ma1.data(), ma2.data()).parameter


def calc_r_work(ma1: miller.array, ma2: miller.array) -> float:
  return ma1.r1_factor(ma2, scale_factor=Auto, assume_index_matching=True)


def calc_significance(ma1: miller.array, _: miller.array) -> float:
  try:
    return flex.mean(ma1.data() / ma1.sigmas())
  except TypeError as e:
    raise NotImplementedError('No sigmas to read from diffBragg .npz') from e


class StatKind(Enum):
  PEARSON_R = 'PearsonR'
  CC = 'cc'
  R_WORK = 'Rwork'
  SIGNIFICANCE = 'significance'

  @property
  def function(self) -> Callable:
    return calc_pearson_r if self is self.PEARSON_R \
      else calc_cc_parameter if self is self.CC \
      else calc_r_work if self is self.R_WORK else calc_significance


class StatInput(Enum):
  F = 'F'
  ANOM = 'anom'


class Stat(Enum):
  PEARSON_R_F = 'PearsonR_F'
  PEARSON_R_ANOM = 'PearsonR_anom'
  CC_F = 'cc_F'
  CC_ANOM = 'cc_anom'
  R_WORK_F = 'Rwork_F'
  R_WORK_ANOM = 'Rwork_anom'
  SIGNIFICANCE_F = 'significance_F'
  SIGNIFICANCE_ANOM = 'significance_anom'

  @property
  def kind(self):
    return StatKind(self.value.split('_', 1)[0])

  @property
  def input(self):
    return StatInput(self.value.rsplit('_', 1)[1])


def evaluate_iteration(
    ma_db: miller.array,  # diffBragg-refined sfs for Pearson's r calc.
    ma_gt: miller.array,  # ground-truth sfs for Pearson's r calc.
    ma_cm: miller.array,  # conventional merging sfs for index selection
    stat: Stat,  # Statistic to calculate:PearsonR/CC/Rwork/significance_F/anom
    scatter_label: int = None,  # If not None, make a scatter plot
    ) -> pd.Series:
  """Calculate `stat` between `ma_db` and `ma_gt` for data in `ma_cm`"""
  binner = ma_gt.binner()
  ma_db = ma_db.common_set(ma_cm)
  ma_db, ma_gt = ma_db.common_sets(ma_gt)
  ma_db.use_binning(binner)
  ma_gt.use_binner_of(ma_db)
  binner = ma_gt.binner()
  stats_binned = []
  bin_ranges = []
  db_data_binned = []
  gt_data_binned = []
  for i_bin in binner.range_used():
    bin_selection = binner.selection(i_bin)
    ma_db_selection = ma_db.select(bin_selection)
    ma_gt_selection = ma_gt.select(bin_selection)
    try:
      stats_binned.append(stat.kind.function(ma_db_selection, ma_gt_selection))
    except ValueError:
      stats_binned.append(np.nan)
    bin_ranges.append(binner.bin_d_range(i_bin))
    if scatter_label is not None:
      db_data_binned.append(ma_db_selection.data())
      gt_data_binned.append(ma_gt_selection.data())
  print(f'{stat.value}: {stats_binned}')
  if scatter_label is not None:
    plot_scatters(db_data_binned, gt_data_binned, scatter_label)
  return pd.Series(data=stats_binned, index=bin_ranges)


def plot_scatters(db_data_binned: List[Sequence[float]],  # plot along x axis
                  gt_data_binned: List[Sequence[float]],  # plot along y axis
                  label: str) -> None:        # label used in saved file name
  """Prepare and save a pair of xs vs ys plots, colored according to bin"""
  fig, axes = plt.subplots(nrows=1, ncols=2)
  for i_bin, (x, y) in enumerate(zip(db_data_binned, gt_data_binned)):
    axes[0].plot(x, y, '.', color=bin_colors[i_bin])
    axes[1].loglog(abs(x), abs(y), '.', color=bin_colors[i_bin])
  axes[0].axline((0., 0.), (1., 1.), color='r')
  axes[1].axline((0., 0.), (1., 1.), color='r')
  axes[0].set_xlabel(f'refined data, step {label}')
  axes[0].set_ylabel(f'ground truth data')
  axes[1].set_xlabel(f'(log scale)')
  fig.savefig(f'scatter_{label}.png')


def run(parameters) -> None:
  # set up paths, convenience classes, global variables
  bin_colors_pos = [(i + .5) / parameters.n_bins for i in range(parameters.n_bins)]
  bin_colors.extend(plt.get_cmap("viridis")(bin_colors_pos))
  stat = Stat(parameters.stat)
  input_path = get_stage2_path(parameters)  # diffBragg stage2 output dir
  mtz_path = get_mtz_path(parameters)  # conventional merging mtz file
  pdb_path = get_pdb_path(parameters)  # ground truth structure factors
  symmetry = iotbx.pdb.input(pdb_path).crystal_symmetry()
  scatter_idx = expand_integer_ranges(parameters.scatter_ranges)

  # generate ground truth data
  ma_gt = get_complex_fcalc_from_pdb(pdb_path, wavelength=parameters.wavelength,
                                     dmin=parameters.d_min, dmax=parameters.d_max)
  ma_gt = ma_gt.as_amplitude_array()
  if stat.input is StatInput.ANOM:
    ma_gt = ma_gt.anomalous_differences()
  ma_gt.setup_binner(d_min=parameters.d_min, d_max=parameters.d_max, n_bins=parameters.n_bins)

  # Read reference: output of conventional merging used to select compared data
  ma_ref = iotbx.mtz.object(mtz_path).as_miller_arrays()[0]
  ma_ref = ma_ref.as_amplitude_array()
  if stat.input is StatInput.ANOM:
    ma_ref = ma_ref.anomalous_differences()
  scatter_id = 'DIALS' if 1 in scatter_idx else None
  stat_binned = evaluate_iteration(ma_ref, ma_gt, ma_ref, stat, scatter_id)
  stats_binned_steps = [stat_binned]

  # iterate over and evaluate all npz files present
  if parameters.is_ens_hopper:
    all_mtz_files =glob.glob(input_path + '/optimized_channel0_iter*.mtz')
    get_iter = lambda x: int(x.split("channel0_iter")[1].split(".mtz")[0])
    all_mtz_files = sorted(all_mtz_files, key=get_iter)
    all_iters = len(all_mtz_files)
  else:
    f_asu_map = np.load(input_path + '/f_asu_map.npy', allow_pickle=True)[()]
    all_npz_files = glob.glob(input_path + '/_fcell_trial0_eval*_iter*.npz')
    if len(all_npz_files)==0:
      all_npz_files = glob.glob(input_path + '/_fcell_trial0_iter*.npz')
      all_npz_files.sort(key=natural_sort)
      parameters.all_evaluations = True
    if not parameters.all_evaluations:
      iteration_files = {}
      for filename in all_npz_files:
        _, _, trial, eval_count, iter = filename.split("/")[-1].split(".")[0].split("_")
        eval_count = int(eval_count[4:])
        iter = int(iter[4:])
        if iter in iteration_files:
          if iteration_files[iter]['eval_count'] >= eval_count:
            continue
        iteration_files[iter] = {'name':filename, 'eval_count':eval_count}
      all_npz_files = [iteration_files[x]['name'] for x in range(len(iteration_files))]
    all_iters = len(all_npz_files)
  for num_iter in range(0, all_iters, parameters.stride):
    if parameters.is_ens_hopper:
      mtz_file = all_mtz_files[num_iter]
      print(mtz_file)
      ma = any_reflection_file(mtz_file).as_miller_arrays()[0]
    else:
      npz_file = all_npz_files[num_iter]
      mtz_path = os.path.splitext(npz_file)[0] + '.mtz'
      try:
        ma = any_reflection_file(mtz_path).as_miller_arrays()[0]
        print(mtz_path)
      except Sorry:
        print(npz_file)
        ma = read_npz(npz_file, f_asu_map, symmetry, save_mtz=parameters.save_mtz)

    if stat.input is StatInput.ANOM:
      ma = ma.anomalous_differences()

    scatter_id = f'diffBragg{num_iter}' if num_iter in scatter_idx else None
    stat_binned = evaluate_iteration(ma, ma_gt, ma_ref, stat, scatter_id)
    stats_binned_steps.append(stat_binned)
  stats_dataframe = pd.concat(stats_binned_steps, axis=1)

  # Plot stat as a function of iteration
  indices = [-1] + list(range(0,all_iters, parameters.stride))
  plt.close("all")  # remove all previously generated figures from memory
  fig, axes = plt.subplots()
  for bin_i, (bin_range, stats_row) in enumerate(stats_dataframe.iterrows()):
    bin_label = bin_label_from(bin_range)
    axes.plot(indices, stats_row, '-', color=bin_colors[bin_i], label=bin_label)
  axes.set_xlabel('diffBragg iteration step')
  axes.set_ylabel(stat.value)
  if parameters.n_bins > 1:
    if parameters.legend == 'corner':
      axes.legend(loc='lower right')
    elif parameters.legend == 'top':
      axes.legend(bbox_to_anchor=(0.5, 1.005), bbox_transform=fig.transFigure,
                  ncol=3, handletextpad=.1, borderpad=.2, loc='upper center')
  axes.grid(1, ls='--')
  fig.savefig(parameters.figprefix + stat.value + '.png')

  if parameters.show:
    plt.show()


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
