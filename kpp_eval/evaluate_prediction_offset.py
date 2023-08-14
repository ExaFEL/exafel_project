"""
Calculate, compare, and report the offset of observed vs predicted reflection
position in DIALS' stills_process vs diffBragg's hopper (stage 1).
"""
from collections import OrderedDict, UserList
from itertools import chain
import glob
from typing import Callable, List, NamedTuple
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
  .help = If None, $SCRATCH/psii/$JOB_ID_HOPPER/stage1 will be used.
expt = None
  .type = str
  .help = Path to an expt files containing reference detector model. If None,
  .help = the first expt file found in stage1/expers/rank0/ will be used.
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
"""


NJ = 1
COMM = MPI.COMM_WORLD


def print0(*args: str, **kwargs):
  if COMM.rank == 0:
    print(*args, **kwargs)


@set_default_return('$SCRATCH/psii/$JOB_ID_HOPPER/stage1')
def get_stage1_path(params_) -> str:
  return params_.stage1


def get_expt_path(params_) -> str:
  stage1_path = get_stage1_path(params_)
  default_expt_glob = os.path.join(stage1_path, 'expers/rank0/*.expt')
  default_expt_path = next(glob.iglob(default_expt_glob), None)
  return p if (p := params.expt) else default_expt_path


class BinLimits(UserList):
  """Simple class to generate and store list of resolution bin limits"""
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
  def overall_header(self):
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


def xy_to_polar(refl, detector, dials=False):
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


def offset_polar(refl, detector: Detector, cal_col_name: str) -> np.ndarray:
  """Vectorized version of xy_to_polar, may work faster for many refl/panel"""
  xy_obs = flex.vec2_double(refl['xyzobs.px.value'].as_numpy_array()[:, :2])
  xy_cal = flex.vec2_double(refl[cal_col_name].as_numpy_array()[:, :2])
  rad_component = np.empty((len(refl), ), dtype=float)
  tang_component = np.empty((len(refl), ), dtype=float)

  panel_id_used = list(set(refl['panel']))
  for panel_id in panel_id_used:
    panel = detector[panel_id]
    sel = refl['panel'] == panel_id
    xy_obs_sel = xy_obs.select(sel)
    xy_cal_sel = xy_cal.select(sel)
    xy_obs_mm = panel.pixel_to_millimeter(xy_obs_sel)
    xy_cal_mm = panel.pixel_to_millimeter(xy_cal_sel)
    xy_obs_lab = np.array(panel.get_lab_coord(xy_obs_mm))[:, :2]
    xy_cal_lab = np.array(panel.get_lab_coord(xy_cal_mm))[:, :2]
    xy_delta = xy_obs_lab - xy_cal_lab
    rad_vectors = xy_obs_lab / np.linalg.norm(xy_obs_lab, axis=1)[:, None]
    tang_vectors = np.array([-rad_vectors[:, 1], rad_vectors[:, 0]]).T
    rad_component[sel] = np.abs(np.sum(xy_delta * rad_vectors, axis=1))
    tang_component[sel] = np.abs(np.sum(xy_delta * tang_vectors, axis=1))
  return np.vstack([rad_component, tang_component])


def offsets_from_refl(refl: flex.reflection_table, detector) -> pd.DataFrame:
  r = {}
  xy_obs = refl['xyzobs.px.value'].as_numpy_array()[:, :2]
  xy_cal1 = refl['xyzcal.px'].as_numpy_array()[:, :2]
  xy_cal2 = refl['dials.xyzcal.px'].as_numpy_array()[:, :2]
  r['dB_offset'] = np.sqrt(np.sum((xy_obs - xy_cal1) ** 2, axis=1))
  r['DIALS_offset'] = np.sqrt(np.sum((xy_obs - xy_cal2) ** 2, axis=1))
  r['resolution'] = list(1. / np.linalg.norm(refl['rlp'], axis=1))
  # r['dB_rad'], r['dB_tang'] = zip(
  #   *[xy_to_polar(refl[i_r], detector, dials=False)
  #     for i_r in range(len(refl))])
  # r['DIALS_rad'], r['DIALS_tang'] = zip(
  #   *[xy_to_polar(refl[i_r], detector, dials=True)
  #     for i_r in range(len(refl))])
  r['dB_rad'], r['dB_tang'] = offset_polar(refl, detector, 'xyzcal.px')
  r['DIALS_rad'], r['DIALS_tang'] = offset_polar(refl, detector, 'dials.xyzcal.px')
  return pd.DataFrame.from_records(r)


class OffsetKind(NamedTuple):
  title: str
  dB_col_name: str
  DIALS_col_name: str


offset_kinds = [OffsetKind('Overall', 'dB_offset', 'DIALS_offset'),
                OffsetKind('Radial', 'dB_rad', 'DIALS_rad'),
                OffsetKind('Tangential', 'dB_tang', 'DIALS_tang')]


class OffsetArtist:
  def __init__(self, offset_summary: pd.DataFrame, stat: str):
    self.data = offset_summary
    self.stat = stat

  def plot_offset(self, offset_kind: OffsetKind) -> None:
    fig, ax = plt.subplots()
    fig.set_size_inches((5, 4))
    ax.set_title(offset_kind.title)
    y1 = self.data[offset_kind.dB_col_name]
    y2 = self.data[offset_kind.DIALS_col_name]
    ax.plot(y1, color='chartreuse', marker='s', mec='k')
    ax.plot(y2, color='tomato', marker='o', mec='k')
    ax.set_xticks(list(range(len(self.data.index))))
    ax.set_xticklabels([i.replace('-', '\n-\n') for i in self.data.index])
    ax.tick_params(labelsize=10, length=0)
    ax.grid(visible=True, color="#777777", ls="--", lw=0.5)
    ax.set_xlabel("resolution ($\AA$)", fontsize=11, labelpad=5)
    ax.set_ylabel(self.stat + " of prediction offset (pixels)", fontsize=11)
    ax.set_facecolor('gainsboro')
    plt.subplots_adjust(bottom=0.2, left=0.15, right=0.98, top=0.9)
    legend = ax.legend(("diffBragg", "DIALS"), prop={"size": 10})
    legend_frame = legend.get_frame()
    legend_frame.set_facecolor("bisque")
    legend_frame.set_alpha(1)


def run(parameters) -> None:
  expt_path = get_expt_path(parameters)
  detector = ExperimentList.from_file(expt_path, check_format=False)[0].detector
  refl_glob = os.path.join(get_stage1_path(parameters), 'refls/rank*/*.refl')
  refl_paths = glob.glob(refl_glob)
  print0(f'#refl files: {len(refl_paths)}')
  refl_paths = refl_paths[COMM.rank::COMM.size]
  refl = flex.reflection_table()
  for rp in refl_paths:
    refl.extend(flex.reflection_table.from_file(rp))
  offsets = offsets_from_refl(refl, detector)
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
  oa = OffsetArtist(offset_summary[:-1], parameters.stat)  # no summary row
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
