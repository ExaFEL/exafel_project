"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz and plot
the evolution of Pearson's R or CC1/2 as a function of stage2 progress.
"""
from functools import wraps
from typing import Callable, List, Sequence, Tuple
import numpy as np
import pandas as pd
import os
from matplotlib import pyplot as plt
from scipy.stats import pearsonr
import glob
import iotbx.mtz
import iotbx.pdb
from dials.array_family import flex
from cctbx import miller, crystal
from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb
from exafel_project.kpp_eval.phil import parse, parse_input


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
stat = cc_gt cc_anom *PearsonR_gt
  .type = choice(multi=False)
  .help = List of statistics to be implemented
d_min = 1.9
  .type = float
  .help = If given, lower bound of data resolution to be investigated
d_max = 9999.
  .type = float
  .help = If given, upper bound of data resolution to be investigated
n_bins = 1
  .type = int
  .help = Data will be divided into `bins` resolution ranges for evaluation
scatter_labels = None
  .type = str
  .help = DiffBragg step ranges (in Python convention) to plot ground truth vs
  .help = refined data scatter for, f.e. "0:8:2,10" for steps 0, 2, 4, 6 & 10.
  .help = DIALS merging results can be plotted using step value of -1.
"""
phil_scope = parse(phil_scope_str)


bin_colors = []  # global list of colors for plotting set-up later


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


def evaluate_iteration(
    ma_db: miller.array,  # diffBragg-refined sfs for Pearson's r calc.
    ma_gt: miller.array,  # ground-truth sfs for Pearson's r calc.
    ma_cm: miller.array,  # conventional merging sfs for index selection
    scatter_label: int = None,  # If not None, make a scatter plot
    ) -> List[float]:
  """Calculate Pearson's R between `ma_db` and `ma_gt` for data in `ma_cm`"""
  binner = ma_gt.binner()
  ma_db = ma_db.common_set(ma_cm)
  ma_db, ma_gt = ma_db.common_sets(ma_gt)
  ma_db.use_binning(binner)
  ma_gt.use_binner_of(ma_db)
  binner = ma_gt.binner()
  pearson_rs = []
  bin_ranges = []
  db_data_binned = []
  gt_data_binned = []
  for i_bin in binner.range_used():
    bin_selection = binner.selection(i_bin)
    db_data = ma_db.select(bin_selection).data()
    gt_data = ma_gt.select(bin_selection).data()
    try:
      pearson_rs.append(pearsonr(db_data, gt_data)[0])
    except ValueError:
      pearson_rs.append(np.nan)
    bin_ranges.append(binner.bin_d_range(i_bin))
    if scatter_label is not None:
      db_data_binned.append(db_data)
      gt_data_binned.append(gt_data)
  print('Pearson Rs: ', pearson_rs)
  if scatter_label is not None:
    plot_scatters(db_data_binned, gt_data_binned, scatter_label)
  return pd.Series(data=pearson_rs, index=bin_ranges)


def plot_scatters(xs: List[Sequence[float]],  # values along x axis
                  ys: List[Sequence[float]],  # values along y axis
                  label: str) -> None:        # label used in saved file name
  """Prepare and save a pair of xs vs ys plots, colored according to bin"""
  fig, axes = plt.subplots(nrows=1, ncols=2)
  for i_bin, (x, y) in enumerate(zip(xs, ys)):
    axes[0].scatter(x, y, color=bin_colors[i_bin])
    axes[1].loglog(x, y, color=bin_colors[i_bin])
  plt.savefig(f'scatter_{label}.png')


def run(parameters):
  bin_colors_pos = [(i + .5) / parameters.n_bins for i in range(parameters.n_bins)]
  bin_colors.extend(plt.get_cmap("viridis")(bin_colors_pos))
  input_path = get_stage2_path(parameters)  # diffBragg stage2 output dir
  mtz_path = get_mtz_path(parameters)  # conventional merging mtz file
  pdb_path = get_pdb_path(parameters)  # ground truth structure factors
  symmetry = iotbx.pdb.input(pdb_path).crystal_symmetry()
  ma_calc = get_complex_fcalc_from_pdb(pdb_path, wavelength=1.3, dmin=1.9, dmax=1000)
  ma_calc = ma_calc.as_amplitude_array()
  ma_calc.setup_binner(d_min=parameters.d_min, d_max=parameters.d_max, n_bins=parameters.n_bins)

  # Miller index map
  f_asu_map=np.load(input_path + '/f_asu_map.npy',allow_pickle=True)[()]

  # Output of conventional merging
  ma_proc = iotbx.mtz.object(mtz_path).as_miller_arrays()[0]
  ma_proc = ma_proc.as_amplitude_array()
  pearson_rs_list = [evaluate_iteration(ma_proc, ma_calc, ma_proc)]

  all_iter_npz = len(glob.glob(input_path + '/_fcell_trial0_iter*.npz'))
  for num_iter in range(all_iter_npz):
    npz_file = f'{input_path}/_fcell_trial0_iter{num_iter}.npz'
    print(npz_file)
    ma = read_npz(npz_file, f_asu_map, symmetry, save_mtz=True)
    # import IPython
    # IPython.embed()
    pearson_rs_list.append(evaluate_iteration(ma, ma_calc, ma_proc))
  pearson_rs_dataframe = pd.concat(pearson_rs_list, axis=1)

  # Plot pearson_coeff as a function of iteration
  fig, axes = plt.subplots()
  for bin_i, (bin_label, pearson_rs) in enumerate(pearson_rs_dataframe.iterrows()):
    axes.plot(pearson_rs, '.', color=bin_colors[bin_i], label=bin_label)
  axes.legend()
  plt.savefig('pearson_coeff.png')
  plt.show()


params = []
if __name__ == '__main__':
  params, options = parse_input(phil_scope)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
