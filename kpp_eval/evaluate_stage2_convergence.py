"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz and plot
the evolution of Pearson's R or CC of F or anom as a function of stage2 step.
"""
from enum import Enum
from functools import wraps
import glob
import os
from typing import Callable, Iterable, List, Sequence, Tuple

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from dials.array_family import flex
from cctbx import miller, crystal
import iotbx.mtz
import iotbx.pdb
from exafel_project.kpp_eval.phil import parse, parse_input
from exafel_project.kpp_eval.evaluate_cc12 import CrossCorrelationSums
from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb


phil_scope_str = """
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
stat = cc_gt cc_anom *PearsonR_gt PearsonR_anom
  .type = choice(multi=False)
  .help = The type of statistic to be calculated
d_min = 1.9
  .type = float
  .help = If given, lower bound of data resolution to be investigated
d_max = 9999.
  .type = float
  .help = If given, upper bound of data resolution to be investigated
wavelength = 1.3
  .type = float
  .help = Radiation wavelength used to generate ground-truth data, in Angstrom
n_bins = 1
  .type = int
  .help = Data will be divided into `bins` resolution ranges for evaluation
scatter_ranges = None
  .type = str
  .help = DiffBragg step ranges (in Python convention) to plot ground truth vs
  .help = refined data scatter for, f.e. "0:8:2,10" for steps 0, 2, 4, 6 & 10.
  .help = DIALS merging results can be plotted using step value of -1.
"""
phil_scope = parse(phil_scope_str)


bin_colors = []  # global list of colors used for plotting bins, filled later


def set_default_return(default_path: str) -> Callable:
  """Decorate func so that None return is replaced with default_path instead"""
  def decorator(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
      result = func(*args, **kwargs)
      return os.path.expandvars(default_path) if result is None else result
    return wrapper
  return decorator

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
  """Convert string of int ranges (e.g. "1:4,6") into list ([1, 2, 3, 5])"""
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
             save_mtz: bool = False,
             ) -> miller.array:
  """Read Miller array from .npz and f_asu_map, optionally save it as mtz"""
  f_values = np.load(npz_path)['fvals']
  miller_idx = flex.miller_index([f_asu_map[i] for i in range(len(f_values))])
  miller_set = miller.set(symmetry, miller_idx, True)
  miller_data = flex.double(f_values)
  ma = miller.array(miller_set, miller_data)
  ma = ma.set_observation_type_xray_amplitude()
  if save_mtz:
    mtz_path = os.path.splitext(npz_path)[0] + '.mtz'
    ma.as_mtz_dataset(column_root_label='F').mtz_object().write(mtz_path)
  return ma


def bin_label_from(bin_range: Tuple[float, float]) -> str:
  return '-'.join(['{:.4f}'.format(m if m > 0 else np.nan) for m in bin_range])


def calc_pearson_r(x: Iterable, y: Iterable) -> float:
  return pearsonr(x, y)[0]


def calc_cc_parameter(x: Iterable, y: Iterable) -> float:
  return CrossCorrelationSums.from_xy(x, y).parameter


class StatKind(Enum):
  PEARSON_R_GT = 0
  PEARSON_R_ANOM = 1
  CC_GT = 2
  CC_ANOM = 3

  @classmethod
  def from_param(cls, param: str) -> 'StatKind':
    enum_vals = ['PearsonR_gt', 'PearsonR_anom', 'cc_gt', 'cc_anom']
    return cls(enum_vals.index(param))

  @property
  def anomalous_differences(self) -> bool:
    return bool(self.value % 2)

  @property
  def function(self) -> Callable:
    return calc_pearson_r if self.value < 2 else calc_cc_parameter


def evaluate_iteration(
    ma_db: miller.array,  # diffBragg-refined sfs for Pearson's r calc.
    ma_gt: miller.array,  # ground-truth sfs for Pearson's r calc.
    ma_cm: miller.array,  # conventional merging sfs for index selection
    stat_kind: StatKind,  # What should be calculated, PearsonR/CC_gt/anom
    scatter_label: int = None,  # If not None, make a scatter plot
    ) -> List[float]:
  """Calculate `stat_kind` between `ma_db` and `ma_gt` for data in `ma_cm`"""
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
    db_data = ma_db.select(bin_selection).data()
    gt_data = ma_gt.select(bin_selection).data()
    try:
      stats_binned.append(stat_kind.function(db_data, gt_data))
    except ValueError:
      stats_binned.append(np.nan)
    bin_ranges.append(binner.bin_d_range(i_bin))
    if scatter_label is not None:
      db_data_binned.append(db_data)
      gt_data_binned.append(gt_data)
  print(f'{stat_kind.name}: {stats_binned}')
  if scatter_label is not None:
    plot_scatters(db_data_binned, gt_data_binned, scatter_label)
  return pd.Series(data=stats_binned, index=bin_ranges)


def plot_scatters(db_data_binned: List[Sequence[float]],  # plot along x axis
                  gt_data_binned: List[Sequence[float]],  # plot along y axis
                  label: str) -> None:        # label used in saved file name
  """Prepare and save a pair of xs vs ys plots, colored according to bin"""
  fig, axes = plt.subplots(nrows=1, ncols=2)
  for i_bin, (x, y) in enumerate(zip(db_data_binned, gt_data_binned)):
    axes[0].axline((0., 0.), (1., 1.), color='r')
    axes[0].scatter(x, y, color=bin_colors[i_bin])
    axes[0].set_xlabel(f'refined data, step {label}')
    axes[0].set_ylabel(f'ground truth data')
    axes[1].axline((0., 0.), (1., 1.), color='r')
    axes[1].loglog(x, y, '.', color=bin_colors[i_bin])
    axes[1].set_xlabel(f'(log scale)')
  fig.savefig(f'scatter_{label}.png')


def run(parameters):
  # set up paths, convenience classes, global variables
  bin_colors_pos = [(i + .5) / parameters.n_bins for i in range(parameters.n_bins)]
  bin_colors.extend(plt.get_cmap("viridis")(bin_colors_pos))
  stat_kind = StatKind.from_param(parameters.stat)
  input_path = get_stage2_path(parameters)  # diffBragg stage2 output dir
  mtz_path = get_mtz_path(parameters)  # conventional merging mtz file
  pdb_path = get_pdb_path(parameters)  # ground truth structure factors
  symmetry = iotbx.pdb.input(pdb_path).crystal_symmetry()
  scatter_idx = expand_integer_ranges(parameters.scatter_ranges)

  # generate ground truth data
  ma_gt = get_complex_fcalc_from_pdb(pdb_path, wavelength=parameters.wavelength,
                                     dmin=parameters.d_min, dmax=parameters.d_max)
  ma_gt = ma_gt.as_amplitude_array()
  if stat_kind.anomalous_differences:
    ma_gt = ma_gt.anomalous_differences()
  ma_gt.setup_binner(d_min=parameters.d_min, d_max=parameters.d_max, n_bins=parameters.n_bins)

  # Read reference: output of conventional merging used to select compared data
  ma_ref = iotbx.mtz.object(mtz_path).as_miller_arrays()[0]
  ma_ref = ma_ref.as_amplitude_array()
  if stat_kind.anomalous_differences:
    ma_ref = ma_ref.anomalous_differences()
  scatter_id = 'DIALS' if 1 in scatter_idx else None
  stat_binned = evaluate_iteration(ma_ref, ma_gt, ma_ref, stat_kind, scatter_id)
  stats_binned_steps = [stat_binned]

  # iterate over and evaluate all npz files present
  f_asu_map = np.load(input_path + '/f_asu_map.npy', allow_pickle=True)[()]
  all_iter_npz = len(glob.glob(input_path + '/_fcell_trial0_iter*.npz'))
  for num_iter in range(all_iter_npz):
    npz_file = f'{input_path}/_fcell_trial0_iter{num_iter}.npz'
    print(npz_file)
    ma = read_npz(npz_file, f_asu_map, symmetry, save_mtz=True)
    if stat_kind.anomalous_differences:
      ma = ma.anomalous_differences()
    # import IPython
    # IPython.embed()
    scatter_id = f'diffBragg{num_iter}' if num_iter in scatter_idx else None
    stat_binned = evaluate_iteration(ma, ma_gt, ma_ref, stat_kind, scatter_id)
    stats_binned_steps.append(stat_binned)
  stats_dataframe = pd.concat(stats_binned_steps, axis=1)

  # Plot stat as a function of iteration
  indices = [-1] + list(range(all_iter_npz))
  plt.close("all")  # remove all previously generated figures from memory
  fig, axes = plt.subplots()
  for bin_i, (bin_range, stats_row) in enumerate(stats_dataframe.iterrows()):
    bin_label = bin_label_from(bin_range)
    axes.plot(indices, stats_row, '-', color=bin_colors[bin_i], label=bin_label)
  axes.set_xlabel('diffBragg iteration step')
  axes.set_ylabel(stat_kind.name)
  if parameters.n_bins > 1:
    axes.legend(loc='lower right')
  fig.savefig(stat_kind.name.lower() + '.png')
  plt.show()


params = []
if __name__ == '__main__':
  params, options = parse_input(phil_scope)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
