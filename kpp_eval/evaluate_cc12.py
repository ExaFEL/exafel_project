"""
This python script allows calculations of cross-correlation between two mtz
files. It is based on many methods in `cctbx.xfel.merge` routine, see files:

* xfel/merging/application/model/crystal_model.py
* xfel/merging/application/model/resolution_binner.py
* xfel/merging/application/statistics/intensity_resolution_statistics.py
"""

import math
from typing import Dict, Iterable, NamedTuple, List

import numpy as np
from cctbx import miller
from cctbx.crystal import symmetry
from iotbx import reflection_file_reader as refl_file_reader

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
mtz = None
  .type = str
  .multiple = True
  .help = Individual paths to the mtz files to be evaluated against each other.
d_min = None
  .type = float
  .help = Lower bound of data resolution to be investigated, in Angstrom
"""


class CrossCorrelationBin(NamedTuple):
  """Storage class for parameters of a cross-correlation resolution bin"""
  i_bin: int = None
  theoretical_asu_count: int = 0,
  observed_matching_asu_count: int = 0,
  cross_correlation: float = None


class CrossCorrelationSums(NamedTuple):
  """Storage class for counts and sums used to calculate cross-correlation"""
  count: int = 0
  sum_xx: float = 0.0
  sum_yy: float = 0.0
  sum_xy: float = 0.0
  sum_x: float = 0.0
  sum_y: float = 0.0

  @classmethod
  def from_xy(cls, x: Iterable, y: Iterable) -> 'CrossCorrelationSums':
    x, y = np.array(x), np.array(y)
    return cls(len(x), sum(x * x), sum(y * y), sum(x * y), sum(x), sum(y))

  def __add__(self, other):
    return CrossCorrelationSums(*[s + o for s, o in zip(self, other)])

  def __radd__(self, other):
    return self if other == 0 else self.__add__(other)

  @property
  def parameter(self):
    numerator = (self.count * self.sum_xy - self.sum_x * self.sum_y)
    denominator = (math.sqrt(self.count * self.sum_xx - self.sum_x ** 2) *
                   math.sqrt(self.count * self.sum_yy - self.sum_y ** 2))
    return numerator / denominator if denominator else 0.0


class CrossCorrelationTable(object):
  """Represents a table of cross-correlations for resolution bins"""
  def __init__(self, binner) -> None:
    self.binner = binner
    self.cc_bins = []
    self.cumulative_observed_matching_asu_count = 0
    self.cumulative_theor_asu_count = 0
    self.cumulative_cross_correlation = 0.0

  def __str__(self) -> str:
    cc_bins_iterator = iter(self.cc_bins)
    s = '    d_max     d_min  #obs_asu / #thr_asu     cc1/2\n'
    s += '-' * 50 + '\n'
    for i_bin in self.binner.range_used():
      ccb: CrossCorrelationBin = next(cc_bins_iterator)
      s += f'({self.binner.bin_d_range(i_bin)[0]:8.4f},' \
           f' {self.binner.bin_d_range(i_bin)[1]:8.4f})' \
           f' {ccb.observed_matching_asu_count:>8d} /' \
           f' {ccb.theoretical_asu_count:>8d}' \
           f' {100*ccb.cross_correlation:8.4f}%\n'
    s += '-' * 50 + '\n'
    i_bins_used = list(self.binner.range_used())
    s += f'({self.binner.bin_d_range(i_bins_used[0])[0]:8.4f},' \
         f' {self.binner.bin_d_range(i_bins_used[-1])[1]:8.4f})' \
         f' {self.cumulative_observed_matching_asu_count:>8d} /' \
         f' {self.cumulative_theor_asu_count:>8d}' \
         f' {100 * self.cumulative_cross_correlation:8.4f}%\n'
    return s

  def build(self, cross_correlation_sums_list: List[CrossCorrelationSums]) -> None:
    """Evaluate values in self based on binner and sums lists provided"""
    cum_cc_sums = CrossCorrelationSums()
    cumulative_theoretical_asu_count = 0

    for i_bin in self.binner.range_used():
      cc_sums = cross_correlation_sums_list[i_bin]
      cc = cc_sums.parameter
      theoretical_count = self.binner.counts()[i_bin]
      cc_bin = CrossCorrelationBin(i_bin, theoretical_count, cc_sums.count, cc)
      self.cc_bins.append(cc_bin)
      cum_cc_sums += cc_sums
      cumulative_theoretical_asu_count += self.binner.counts()[i_bin]

    self.cumulative_observed_matching_asu_count = cum_cc_sums.count
    self.cumulative_theor_asu_count = cumulative_theoretical_asu_count
    self.cumulative_cross_correlation = cum_cc_sums.parameter


def generate_hkl_to_bin_map(binner, miller_set) -> Dict:
  """Generate dict: hkl to bin number for input binner"""
  hkl_to_bin_map = {}  # hkl vs resolution bin number
  for i_bin in binner.range_used():
    bin_hkl_selection = binner.selection(i_bin)
    bin_hkls = miller_set.select(bin_hkl_selection)
    for hkl in bin_hkls.indices():
      hkl_to_bin_map[hkl] = i_bin
  return hkl_to_bin_map


def calculate_cross_correlation(mtz1_path: str, mtz2_path: str,
                                d_min: float = None) -> CrossCorrelationTable:
  """Calculate cc1/2 between two mtz files."""
  ma1 = refl_file_reader.any_reflection_file(mtz1_path).as_miller_arrays()[0]
  ma2 = refl_file_reader.any_reflection_file(mtz2_path).as_miller_arrays()[0]
  d_min = d_min if d_min else max([ma1.d_min(), ma2.d_min()])
  space_group_info = ma1.space_group().info()
  unit_cell = ma1.unit_cell()
  symm = symmetry(unit_cell=unit_cell, space_group_info=space_group_info)
  ms = symm.build_miller_set(anomalous_flag=True, d_max=1000000, d_min=d_min)
  ms.setup_binner(d_max=100000, d_min=d_min, n_bins=10)
  binner = ms.binner()  # as in self.params.statistics.resolution_binner
  hkl_map = generate_hkl_to_bin_map(binner, ms)  # as in .hkl_resolution_bins
  n_bins = binner.n_bins_all()
  cc_sums_list = [CrossCorrelationSums() for _ in range(n_bins)]

  matching_indices = miller.match_multi_indices(
    miller_indices_unique=ma1.indices(),
    miller_indices=ma2.indices())
  for pair in matching_indices.pairs():
    hkl = ma1.indices()[pair[0]]
    assert hkl == ma2.indices()[pair[1]]
    if hkl in hkl_map:
      i_bin = hkl_map[hkl]
      x = ma1.data()[pair[0]]
      y = ma2.data()[pair[1]]
      cc_sums_list[i_bin] += CrossCorrelationSums(1, x**2, y**2, x*y, x, y)
  cct = CrossCorrelationTable(binner=binner)
  cct.build(cc_sums_list)
  return cct


def run(params_) -> None:
  assert len(params_.mtz) == 2, 'Exactly two mtz file paths must be provided'
  mtz_path1, mtz_path2 = params_.mtz[0:2]
  cct = calculate_cross_correlation(mtz_path1, mtz_path2,
                                    d_min=params_.d_min)
  print(str(cct))


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
