from __future__ import division

from dataclasses import dataclass
import glob
from typing import List, Tuple
import sys

from cctbx import crystal, miller
from cctbx.eltbx import henke
from exafel_project.kpp_eval.phil import parse_input
from libtbx import Auto
from iotbx import pdb, reflection_file_reader
from LS49.sim.util_fmodel import gen_fmodel
import mmtbx.command_line.fmodel

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import scipy as sp


message = """
This script aims to compare the quality of two or more MTZ files using a set
of various statistics over a set resolution bins. In the context of the ExaFEL
project, it is designed to validate an improvement of the diffBragg-refined
reflection file compared to the standard DIALS processing. To this aim,
it requires at least three distinct files to be provided as an input:
- MTZ file from a classical DIALS processing pipeline,
- MTZ file from the new diffBragg refinement pipeline,
- PDB file with reference structure used to simulate data.

At the current stage, this script should be run on a single node
via the `evaluate.sh` script, available in this repository.

This is a work in progress.
""".strip()


class RIsoCalculator:
  def __init__(self, anomalous_flag, d_min, d_max, n_bins):
    self.ma1: miller.array = None
    self.ma2: miller.array = None
    self.anomalous_flag = anomalous_flag
    self.d_min = d_min
    self.d_max = d_max
    self.n_bins = n_bins

  @classmethod
  def from_parameters(cls, parameters):
    return NotImplemented

  def _reindex(self) -> None:
    """Make sure that reflections in both sets occupy same asymmetric unit"""
    assert self.ma1.space_group_info().symbol_and_number() ==\
           self.ma2.space_group_info().symbol_and_number()
    self.ma1.change_basis("h,k,l").map_to_asu()
    self.ma2.change_basis("h,k,l").map_to_asu()

  @staticmethod  # revisit
  def _find_common_sets(ma1: miller.array, ma2: miller.array)\
          -> Tuple[miller.array, miller.array]:
    sym = crystal.symmetry(unit_cell=ma1.unit_cell(),
                           space_group_info=ma1.space_group_info())
    common_set2 = ma2.customized_copy(crystal_symmetry=sym).map_to_asu()
    common_set1 = ma1.common_set(common_set2)
    common_set2 = common_set1.common_set(common_set1)
    assert len(common_set1.indices()) == len(common_set2.indices())
    return common_set1, common_set2

  def calculate(self, ma1: miller.array, ma2: miller.array):
    """Calculate binned and total R-factor between two miller arrays"""
    if self.anomalous_flag:
      ma1 = ma1 if ma1.anomalous_flag() else ma1.generate_bijvoet_mates()
      ma2 = ma2 if ma2.anomalous_flag() else ma2.generate_bijvoet_mates()
    assert ma1.space_group_info().symbol_and_number() ==\
           ma2.space_group_info().symbol_and_number()
    ma1 = ma1.map_to_asu().merge_equivalents().array()
    ma2 = ma2.map_to_asu().merge_equivalents().array()
    common_set1, common_set2 = self._find_common_sets(ma1, ma2)
    ma1 = ma1.select_indices(common_set1.indices())
    ma2 = ma2.select_indices(common_set2.indices())
    ma1.setup_binner(d_min=self.d_min, d_max=self.d_max, n_bins=self.n_bins)
    return ma1.r1_factor(ma2, scale_factor=Auto, use_binning=True)


class MillerEvaluator:
  SIM_ALGORITHM = 'fft'

  def __init__(self, parameters):
    self.parameters = parameters
    self.pdb: pdb = self.initialize_pdb()
    self.symmetry: crystal.symmetry = self.initialize_symmetry()
    self.miller_arrays: List[miller.array] = self.initialize_arrays()
    self.miller_reference: miller.array = self.initialize_reference()
    self.initialize_binning()
    self.d_max = 1000.

  def initialize_arrays(self) -> List[miller.array]:
    """Current implem. reads: 1) Iobs,SIGIobs, 2=1) IMEAN,SIGIMEAN, 3) Iobs(+),
    SIGIobs(+),Iobs(-),SIGIobs(-), 4=2 for some data. See .show_summary"""
    miller_arrays = []
    for mtz_path in self.parameters.input.mtz:
      mtz = reflection_file_reader.any_reflection_file(file_name=mtz_path)
      mas = mtz.as_miller_arrays(crystal_symmetry=self.symmetry)
      miller_arrays.append(mas[1])  # reads:
    return miller_arrays

  def initialize_binning(self):
    n_bins = self.parameters.statistics.n_bins
    self.miller_reference.setup_binner(d_min=self.d_min, n_bins=n_bins)
    for ma in self.miller_arrays:
      ma.use_binning_of(self.miller_reference)

  def initialize_pdb(self) -> pdb:
    return pdb.input(file_name=self.parameters.input.pdb)

  def initialize_reference(self) -> miller.array:
    """Create reference miller array using `LS49.sim.util_fmodel.gen_fmodel`"""
    pdb_text = open(self.parameters.input.pdb, "r").read()
    f_model = gen_fmodel(
      resolution=self.d_min, pdb_text=pdb_text, algorithm=self.SIM_ALGORITHM,
      wavelength=self.parameters.input.wavelength)
    return f_model.get_amplitudes() if self.parameters.input.anomalous_flag \
        else f_model.get_amplitudes().as_non_anomalous_array()

  def initialize_symmetry(self) -> crystal.symmetry:
    return self.pdb.crystal_symmetry()

  @property
  def d_min(self) -> float:
    return min(ma.d_min() for ma in self.miller_arrays)

  # based on iotbx/command_line/reflection_statistics.py, lines 82-87
  def _evaluate_completeness(self) -> None:
    """Bin & evaluate completeness of each Miller array, plot them together"""
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      ma_without_absences.completeness(use_binning=True).show()

  def _evaluate_i_over_sigma(self) -> None:
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      ma_without_absences.i_over_sig_i(use_binning=True).show()

  def _evaluate_r_factor(self) -> None:
    """Based heavily on xfel/command_line/riso.py by Iris Young. TODO: unify"""
    f_calc = self.miller_reference
    r_iso_calc = RIsoCalculator(
      anomalous_flag=False, d_min=self.d_min,
      d_max=self.d_max, n_bins=self.parameters.statistics.n_bins)
    for ma in self.miller_arrays:
      f_obs = ma.as_amplitude_array()
      r_iso = r_iso_calc.calculate(f_calc, f_obs)
      r_iso.show()

  def evaluate(self):
    statistic_method_map = {'cplt': self._evaluate_completeness,
                            'I/si': self._evaluate_i_over_sigma,
                            'R': self._evaluate_r_factor}
    for statistic in self.parameters.statistics.kind:
      statistic_method_map[statistic]()


def run(params_):
  ev = MillerEvaluator(parameters=params_)
  print(f'{type(ev.miller_reference)=}')
  for ma in ev.miller_arrays:
    print(f'{type(ma)=}')
  ev.evaluate()


params = []
if __name__ == '__main__':
  params, options = parse_input()  # test how to use this reader correctly
  if '-h' in options or '--help' in options:
    print(message)
    exit()
  run(params)
