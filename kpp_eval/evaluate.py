from __future__ import division

from dataclasses import dataclass
import glob
from typing import List
import sys

from cctbx import crystal, miller
from cctbx.eltbx import henke
from exafel_project.kpp_eval.phil import parse_input
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


class MillerEvaluator:
  SIM_ALGORITHM = 'fft'

  def __init__(self, parameters):
    self.parameters = parameters
    self.pdb: pdb = self.initialize_pdb()
    self.symmetry: crystal.symmetry = self.initialize_symmetry()
    self.miller_arrays: List[miller.array] = self.initialize_arrays()
    self.miller_reference: miller.array = self.initialize_reference()
    self.initialize_binning()

  def initialize_arrays(self) -> List[miller.array]:
    miller_arrays = []
    for mtz_path in self.parameters.input.mtz:
      mtz = reflection_file_reader.any_reflection_file(file_name=mtz_path)
      ma = mtz.as_miller_arrays(crystal_symmetry=self.symmetry)
      miller_arrays.extend(ma)
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
    return f_model.get_amplitudes()

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
    print(self.miller_reference.observation_type())
    print(self.miller_reference.is_complex_array())
    print(self.miller_reference.is_xray_amplitude_array())
    for ma in self.miller_arrays:
      print(ma.observation_type())
      print(ma.is_complex_array())
      print(ma.is_xray_amplitude_array())
      ma.r1_factor(other=self.miller_reference, use_binning=True)

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
