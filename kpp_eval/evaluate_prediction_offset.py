"""
Calculate, compare, and report the offset of observed vs predicted reflection
position refined by DIALS' stills_process versus diffBragg's hopper (stage 1).

This script can accept two input kinds. The first one is stage 1 refl files,
containing columns `xyzobs.px.value`, `xyzcal.px`, and `dials.xyzcal.px`.
produced whenever stage 1 is run in debug mode.
The second accepted input is predict pickle and expt files. Using these,
the script can reconstruct all stage 1 information by matching experiments.
The input is chosen automatically depending on which phil paths are specified.
If both stage1 and predict are specified, stage1 input is prioritised.

The script produces two kinds of output: offsets table and plots.
It can be significantly sped up by running it in parallel using `srun`,
however in this configuration offset plots will not be produced.
In order to run script using MPI and obtain plots, first run script using
`srun` with `cache` specified, and then read in the `cache` and replot
the figures without recalculating data by `source`ing the script without MPI.
"""
from collections import OrderedDict, UserList
from enum import Enum
from functools import lru_cache
from glob import glob
from itertools import chain
import math
import pickle
import random
from typing import Callable, List, NamedTuple, Tuple
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cctbx.miller import match_indices
from dials.array_family import flex
from dxtbx.model import Detector, ExperimentList
from libtbx.mpi4py import MPI

from exafel_project.kpp_eval.phil import parse_phil
from exafel_project.kpp_eval.util import set_default_return

# plt.ggplot()
# plt.xkcd()


phil_scope_str = """
stage1 = None
  .type = str
  .help = Directory with stage 1 results, the one containing folder refls.
  .help = If None, ./$JOB_ID_HOPPER/stage1 will be used. (Input kind 1)
predict = None
  .type = str
  .help = Directory with predict results containing `preds_for_hopper.pkl`
  .help = and `expts_and_refls/` directory.
  .help = If None, ./$JOB_ID_PREDICT/predict will be used. (Input kind 2)
expt = None
  .type = str
  .help = Path to an expt files containing reference detector model. If None,
  .help = the first expt file found in stage1/ or predict/ will be used.
fraction = 1.0
  .type = float
  .help = Investigate data from stage1/predict for fraction of data only.
  .help = Set to lower value for testing or if high accuracy is not necessary.
d_min = 1.9
  .type = float
  .help = Lower bound of data resolution to be investigated, in Angstrom
d_max = 9999.
  .type = float
  .help = Upper bound of data resolution to be investigated
n_bins = 10
  .type = int
  .help = Data will be divided into `n_bins` resolution ranges for evaluation
bins_type = same_count *same_volume
  .type = choice(multi=False)
  .help = Type of algorithm to be used when producing resolution bins
stat = *median average rms
  .type = choice(multi=False)
  .help = Which statistic should be evaluated
cache = None
  .type = str
  .help = If given & cache does not exist, write results to cache pickle.
  .help = If given & cache exists, read and show results instead of calculating.
ecp_report = True
  .type = bool
  .help = Increase font size, add enumeration etc. for ECP report
"""


COMM = MPI.COMM_WORLD
RANDOM_SEED = 1337
random.seed(RANDOM_SEED)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)


def print0(*args: str, **kwargs):
  if COMM.rank == 0:
    print(*args, **kwargs)


@set_default_return('./$JOB_ID_HOPPER/stage1')
def get_stage1_path(params_) -> str:
  return params_.stage1


@set_default_return('./$JOB_ID_PREDICT/predict')
def get_predict_path(params_) -> str:
  return params_.predict


class InputKind(Enum):
  stage1 = 1
  predict = 2


class Input(NamedTuple):
  kind: InputKind
  expts: List[str]         # from stage1 or predict, for geometry and id match
  refls: List[str] = None  # from stage1, for dials (& dB if kind 1) xyzcal.px
  pickle: str = None   # from predict, for id map (for dB xyzcal.px if kind 2)

  @classmethod
  def from_params(cls, params_) -> 'Input':
    stage1_path = get_stage1_path(params_)
    stage1_expt_glob = os.path.join(stage1_path, 'expers/rank*/*.expt')
    stage1_refl_glob = os.path.join(stage1_path, 'refls/rank*/*.refl')
    stage1_expt_paths = glob(stage1_expt_glob)
    stage1_refl_paths = glob(stage1_refl_glob)

    predict_path = get_predict_path(params_)
    predict_expt_glob = os.path.join(predict_path, 'expts_and_refls/*.expt')
    predict_pkl_glob = os.path.join(predict_path, 'preds_for_hopper.pkl')
    predict_expt_paths = glob(predict_expt_glob)
    predict_pkl_paths = glob(predict_pkl_glob)
    if stage1_expt_paths and stage1_refl_paths:
      return Input(InputKind.stage1, stage1_expt_paths, refls=stage1_refl_paths)
    elif predict_expt_paths and predict_pkl_paths:
      return Input(InputKind.predict, predict_expt_paths, pickle=predict_pkl_paths[0])
    else:
      msg = 'No stage1 expt/refls or predict expt/pickle were found at globs: '
      globs = (stage1_expt_glob, stage1_refl_glob, predict_expt_glob, predict_pkl_glob)
      raise ValueError(msg + ' '.join(globs))

  @property
  def detector(self) -> Detector:
    d = ExperimentList.from_file(self.expts[0], check_format=False)[0].detector \
      if COMM.rank == 0 else None
    return COMM.bcast(d, root=0)

  @property
  def scattered(self) -> 'Input':
    expts = self.expts[COMM.rank::COMM.size]
    refls = self.refls[COMM.rank::COMM.size] if self.refls else []
    return Input(self.kind, expts, refls=refls, pickle=self.pickle)


class OffsetDataFrames(UserList):
  """Storage class w/ convenience methods for calculating offsets from input"""
  @classmethod
  def from_input(cls, input_, fraction: float = 1.) -> 'OffsetDataFrames':
    if input_.kind is InputKind.stage1:
      return cls._from_stage1_input(input_, fraction)
    else:  # if input_.kind is InputKind.predict
      return cls._from_predict_input(input_, fraction)

  @classmethod
  def _from_stage1_input(cls, input_: Input, fraction) -> 'OffsetDataFrames':
    print0(f'Total refl file count: {len(input_.refls)}')
    detector = input_.detector
    refl_paths = input_.scattered.refls
    if fraction != 1.0:
      refl_paths_n = math.ceil(len(refl_paths) * fraction)
      refl_paths = random.sample(refl_paths, refl_paths_n, )
    return cls(o for rp in refl_paths
               if (o := offsets_from_path(rp, detector)) is not None)

  @staticmethod
  @lru_cache(maxsize=2)
  def get_refl(refl_path: str) -> flex.reflection_table:
    return flex.reflection_table.from_file(refl_path)

  @classmethod
  def _from_predict_input(cls, input_: Input, fraction) -> 'OffsetDataFrames':
    detector = input_.detector
    useful_keys = ['stage1_refls', 'old_exp_idx', 'predictions', 'exp_idx']
    df = pd.read_pickle(input_.pickle)[useful_keys] if COMM.rank == 0 else None
    if COMM.rank == 0:
      print0(f'Total refl file count: {df["stage1_refls"].nunique()}')
    if COMM.rank == 0 and fraction != 1.0:
      df = df.sample(frac=fraction, random_state=RANDOM_SEED, axis=0)
    df = COMM.bcast(df, root=0)
    df = pd.concat([d for i, (_, d) in enumerate(df.groupby('predictions'))
                    if i % COMM.size == COMM.rank])
    df.sort_values(by=['predictions', 'stage1_refls'], inplace=True)
    offsets = []
    for _, event in df.iterrows():
      index_refl = cls.get_refl(event['stage1_refls'])
      index_sel = flex.bool(index_refl['id'] == event['old_exp_idx'])
      index_refl = index_refl.select(index_sel)
      index_refl.sort('miller_index')
      predict_refl = cls.get_refl(event['predictions'])
      predict_sel1 = flex.bool(predict_refl['id'] == event['exp_idx'])
      predict_sel2 = predict_refl['is_strong']
      predict_refl = predict_refl.select(predict_sel1 & predict_sel2)
      predict_refl.sort('miller_index')
      matches = match_indices(index_refl['miller_index'], predict_refl['miller_index'])
      index_refl = index_refl.select(matches.pairs().column(0))
      predict_refl = predict_refl.select(matches.pairs().column(1))
      predict_refl['xyzobs.px.value'] = index_refl['xyzobs.px.value']
      predict_refl['dials.xyzcal.px'] = index_refl['xyzcal.px']
      offsets.append(offsets_from_refl(predict_refl, detector))
    return cls(offsets)


class BinLimits(UserList):
  """Generate, store list of resolution bin limits, similar to miller.binner"""
  EPS = 1e-9

  @classmethod
  def from_params(cls, data: np.ndarray, params_) -> 'BinLimits':
    if params_.bins_type == 'same_count':
      return cls.with_same_count(data, params_)
    else:  # params_.bins_type == 'same_volume':
      return cls.with_same_volume(data, params_)

  @classmethod
  def with_same_count(cls, data: np.ndarray, params_) -> 'BinLimits':
    d_min = params_.d_min if params_.d_min else min(data)
    d_max = params_.d_max if params_.d_max else max(data)
    data = data[(data >= d_min) & (data <= d_max)]
    lims = np.quantile(data, q=np.linspace(1., 0., num=params_.n_bins + 1))
    return cls([lims[0] + cls.EPS] + list(lims[1:-1]) + [lims[-1] - cls.EPS])

  @classmethod
  def with_same_volume(cls, data: np.ndarray, params_) -> 'BinLimits':
    s3_min = pow(params_.d_min if params_.d_min else min(data), -3)
    s3_max = pow(params_.d_max if params_.d_max else max(data), -3)
    s3_linespace = np.linspace(s3_min, s3_max, num=params_.n_bins + 1)
    lims = np.flip(np.power(s3_linespace, -1 / 3))
    return cls([lims[0] + cls.EPS] + list(lims[1:-1]) + [lims[-1] - cls.EPS])

  @property
  def bin_headers(self) -> List[str]:
    limits_str = [f'{limit:.6f}'[:6] for limit in self]
    return [f'{b}-{e}' for b, e in zip(limits_str[:-1], limits_str[1:])]

  @property
  def overall_header(self) -> str:
    return '-'.join([f'{limit:.6f}'[:6] for limit in [self[0], self[-1]]])


class StatCalculatorsRegistry(OrderedDict):
  def register(self, name: str) -> Callable:
    """Register a `func` which calculates `params.stat` from 1D input array"""
    def decorator(func: Callable) -> Callable:
      self[name] = func
      return func
    return decorator
stat_calculators = StatCalculatorsRegistry()

@stat_calculators.register('median')
def calculate_median(data: np.ndarray) -> float:
  return np.median(data)

@stat_calculators.register('average')
def calculate_mean(data: np.ndarray) -> float:
  return np.mean(data)

@stat_calculators.register('rms')
def calculate_rms(data: np.ndarray) -> float:
  return np.sqrt(np.mean(data ** 2))


def xy_to_polar(refl, detector: Detector, dials: bool = False) -> Tuple[float, float]:
  x, y, _ = refl["xyzobs.px.value"]
  if dials:
    xcal, ycal, _ = refl["dials.xyzcal.px"]
  else:
    xcal, ycal, _ = refl["xyzcal.px"]

  pid = refl['panel']
  panel = detector[pid]
  x, y = panel.pixel_to_millimeter((x, y))
  xcal, ycal = panel.pixel_to_millimeter((xcal, ycal))

  xyz_lab = panel.get_lab_coord((x, y))
  xyz_cal_lab = panel.get_lab_coord((xcal, ycal))

  diff = np.array(xyz_lab) - np.array(xyz_cal_lab)

  xy_lab = np.array((xyz_lab[0], xyz_lab[1]))
  rad = xy_lab / np.linalg.norm(xy_lab)
  tang = np.array([-rad[1], rad[0]])

  rad_component = abs(np.dot(diff[:2], rad))
  tang_component = abs(np.dot(diff[:2], tang))
  pxsize = panel.get_pixel_size()[0]
  return rad_component / pxsize, tang_component / pxsize


def offsets_from_path(refl_path: str, detector: Detector) -> pd.DataFrame:
  refl = flex.reflection_table.from_file(refl_path)
  return offsets_from_refl(refl, detector)

def offsets_from_refl(refl: flex.reflection_table, detector) -> pd.DataFrame:
  if len(refl) == 0:
    return None
  r = {}
  xy_obs = refl['xyzobs.px.value'].as_numpy_array()[:, :2]
  xy_cal1 = refl['xyzcal.px'].as_numpy_array()[:, :2]
  xy_cal2 = refl['dials.xyzcal.px'].as_numpy_array()[:, :2]
  r['dB_offset'] = np.sqrt(np.sum((xy_obs - xy_cal1) ** 2, axis=1))
  r['DIALS_offset'] = np.sqrt(np.sum((xy_obs - xy_cal2) ** 2, axis=1))
  r['resolution'] = list(1. / np.linalg.norm(refl['rlp'], axis=1))
  r['dB_rad'], r['dB_tang'] = zip(
    *[xy_to_polar(refl[i_r], detector, dials=False)
      for i_r in range(len(refl))])
  r['DIALS_rad'], r['DIALS_tang'] = zip(
    *[xy_to_polar(refl[i_r], detector, dials=True)
      for i_r in range(len(refl))])
  return pd.DataFrame.from_records(r)


class OffsetKind(NamedTuple):
  enum: str
  title: str
  dB_col_name: str
  DIALS_col_name: str


offset_kinds = [
  OffsetKind('a) ', 'Overall', 'dB_offset', 'DIALS_offset'),
  OffsetKind('b) ', 'Radial', 'dB_rad', 'DIALS_rad'),
  OffsetKind('c) ', 'Tangential', 'dB_tang', 'DIALS_tang')]


class OffsetArtist:
  def __init__(self, offset_summary: pd.DataFrame, params_) -> None:
    self.data = offset_summary
    self.params = params_


  @property
  def font_size(self):
    return 14 if self.params.ecp_report else 10

  def plot_offset(self, offset_kind: OffsetKind) -> None:
    fig, ax = plt.subplots()
    fig.set_size_inches((5, 4))
    title = (offset_kind.enum if self.params else '') + offset_kind.title
    ax.set_title(title, fontsize=self.font_size, pad=15)
    x = [i + 0.5 for i in range(len(self.data.index))]
    y1 = self.data[offset_kind.dB_col_name]
    y2 = self.data[offset_kind.DIALS_col_name]
    ax.plot(x, y1, color='chartreuse', marker='s', mec='k')
    ax.plot(x, y2, color='tomato', marker='o', mec='k')
    ax.set_xticks(list(range(len(self.data.index) + 1)))
    x_ticks = ['inf'] + [i.rsplit('-', 1)[1][:4] for i in self.data.index]
    y_label = self.params.stat + " of prediction offset (pixels)"
    ax.set_xticklabels(x_ticks)
    ax.tick_params(labelsize=self.font_size, length=0)
    ax.grid(visible=True, color="#777777", ls="--", lw=0.5)
    ax.set_xlabel("resolution ($\AA$)", fontsize=self.font_size, labelpad=5)
    ax.set_ylabel(y_label, fontsize=self.font_size)
    ax.set_facecolor('gainsboro')
    plt.subplots_adjust(bottom=0.15, left=0.15, right=0.95, top=0.9)
    legend = ax.legend(("diffBragg", "DIALS"), prop={"size": self.font_size})
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor("bisque")
    legend_frame.set_alpha(1)


def run(parameters) -> None:
  try:
    with open(parameters.cache, 'rb') as cache:
      if COMM.rank == 0:
        offset_summary, parameters.stat = pickle.load(cache)
  except (EOFError, FileNotFoundError, TypeError):
    input_ = Input.from_params(parameters)
    offsets = OffsetDataFrames.from_input(input_, fraction=parameters.fraction)
    offsets_gathered = COMM.gather(offsets)
    if COMM.rank != 0:
      return
    offsets_list = chain.from_iterable(offsets_gathered)
    offsets = pd.concat(offsets_list, axis=0, ignore_index=True)
    bin_limits = BinLimits.from_params(offsets['resolution'], parameters)
    offsets['bin'] = np.digitize(offsets['resolution'], bin_limits) - 1
    stat_calc = stat_calculators[parameters.stat]
    offsets_total = offsets.apply(stat_calc, axis=0, raw=True)
    offsets_binned = [offsets[offsets['bin'] == b].apply(stat_calc, axis=0, raw=True)
                      for b in range(parameters.n_bins)]
    offset_summary = pd.concat(offsets_binned + [offsets_total], axis=1).T
    offset_summary['bin'] = bin_limits.bin_headers + [bin_limits.overall_header]
    offset_summary.set_index('bin', inplace=True)
    print0(offset_summary)
    if parameters.cache:
      with open(parameters.cache, 'wb') as cache:
         pickle.dump((offset_summary, parameters.stat), cache)
  else:
    if COMM.rank != 0:
      return
    print0(offset_summary)
  oa = OffsetArtist(offset_summary[:-1], parameters)  # no summary row
  for offset_kind in offset_kinds:
    oa.plot_offset(offset_kind)
  plt.show()


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
