"""Tools for calculating cc1/2 between two mtz files."""

import math
from typing import NamedTuple, List

from cctbx import miller
from cctbx.crystal import symmetry
from iotbx import reflection_file_reader as refl_file_reader


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

  def __add__(self, other):
    return CrossCorrelationSums(*[s + o for s, o in zip(self, other)])

  def __radd__(self, other):
    return self if other == 0 else self.__add__(other)


class CrossCorrelationTable(object):
  """Represents a table of cross-correlations for resolution bins"""
  def __init__(self, binner):
    self.binner = None
    self.cc_bins = []
    self.cumulative_observed_matching_asu_count = 0
    self.cumulative_theor_asu_count = 0
    self.cumulative_cross_correlation = 0.0

  def build(self, cross_correlation_sums_list: List[CrossCorrelationSums]):
    cum_cc_sums = CrossCorrelationSums()
    cumulative_theoretical_asu_count = 0

    for i_bin in self.binner.range_used():
      cc_sums = cross_correlation_sums_list[i_bin]
      cc = self.formula(*cc_sums)
      theoretical_count = self.binner.counts()[i_bin]
      cc_bin = CrossCorrelationBin(i_bin, theoretical_count, cc_sums.count, cc)
      self.cc_bins.append(cc_bin)
      cum_cc_sums += cc_sums
      cumulative_theoretical_asu_count += self.binner.counts()[i_bin]

    self.cumulative_observed_matching_asu_count = cum_cc_sums.count
    self.cumulative_theor_asu_count = cumulative_theoretical_asu_count
    self.cumulative_cross_correlation = self.formula(*cum_cc_sums)
    return self

  @staticmethod
  def formula(count, sum_xx, sum_yy, sum_xy, sum_x, sum_y):
    """Calculate cross correlation given count and certain sums"""
    numerator = (count * sum_xy - sum_x * sum_y)
    denominator = (math.sqrt(count * sum_xx - sum_x ** 2) *
                   math.sqrt(count * sum_yy - sum_y ** 2))
    return numerator / denominator if denominator else 0.0


def generate_hkl_to_bin_map(binner):
  """Generate dict: hkl to bin number for input binner"""
  hkl_to_bin_map = {}  # hkl vs resolution bin number
  for i_bin in binner.range_used():
    bin_hkl_selection = binner.selection(i_bin)
    bin_hkls = binner.select(bin_hkl_selection)
    for hkl in bin_hkls.indices():
      hkl_to_bin_map[hkl] = i_bin
  return hkl_to_bin_map


def calculate_cross_correlation(mtz1_path, mtz2_path):
  """Calculate cc1/2 between two mtz files. Based on
  xfel/merging/application/model/crystal_model.py,
  xfel/merging/application/model/resolution_binner.py and
  xfel/merging/application/statistics/intensity_resolution_statistics.py"""
  ma1 = refl_file_reader.any_reflection_file(mtz1_path).as_miller_arrays()[0]
  ma2 = refl_file_reader.any_reflection_file(mtz2_path).as_miller_arrays()[0]
  d_min = min([ma1.d_min(), ma2.d_min()])
  space_group = ma1.space_group().info()
  unit_cell = ma1.unit_cell()
  symm = symmetry(unit_cell=unit_cell, space_group=space_group)
  ms = symm.build_miller_set(anomalous_flag=True, d_max=1000000, d_min=d_min)
  ms.setup_binner(d_max=100000, d_min=d_min, n_bins=10)
  binner = ms.binner()  # as in self.params.statistics.resolution_binner
  hkl_map = generate_hkl_to_bin_map(binner)  # statistics.hkl_resolution_bins
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
  return cct.build(*[list(i) for i in zip(*cc_sums_list)])
