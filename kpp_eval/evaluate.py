from __future__ import division

from typing import Dict, List, Tuple

from cctbx import crystal, miller
from exafel_project.kpp_eval.phil import parse_input
from libtbx import Auto
from iotbx import pdb, reflection_file_reader
from LS49.sim.util_fmodel import gen_fmodel

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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


class RegistryHolder(type):
  """Metaclass which auto-registers every `EvaluatedStatistic` in `REGISTRY`"""
  REGISTRY: Dict[str, 'RegistryHolder'] = {}
  phil_name: str  # Name as used in phil file, used as dict key and file name
  full_name: str  # Full name to be used as plot label
  evaluate_method_name: str  # Used by `MillerEvaluator` to get this statistic
  visualize_method_name: str  # Used by `MillerEvaluationArtist` to visualize

  def __new__(mcs, name, bases, attrs):
    new_cls = type.__new__(mcs, name, bases, attrs)
    if hasattr(new_cls, 'phil_name') and new_cls.phil_name:
      mcs.REGISTRY[new_cls.phil_name] = new_cls
    return new_cls


class EvaluatedStatistic(metaclass=RegistryHolder):
  """Base class which auto-registers all named children in the `REGISTRY`"""


class CompletenessStatistic(EvaluatedStatistic):
  phil_name = 'cplt'
  full_name = 'completeness'
  evaluate_method_name = '_evaluate_completeness'
  visualize_method_name = '_visualize_completeness'


class IntensityOverSigmaStatistic(EvaluatedStatistic):
  phil_name = 'I_over_si'
  full_name = 'Intensity over sigma'
  evaluate_method_name = '_evaluate_i_over_sigma'
  visualize_method_name = '_visualize_i_over_sigma'


class RIsoStatistic(EvaluatedStatistic):
  phil_name = 'Riso'
  full_name = 'R1-factor'
  evaluate_method_name = '_evaluate_r_factor'
  visualize_method_name = '_visualize_r_factor'


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
    self.results = self.initialize_dataframe()

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

  def initialize_dataframe(self):
    binner = self.miller_reference.binner()
    n_rows = binner.n_bins_all()
    data = {'d_max': [binner.bin_d_min(i) for i in range(n_rows)],
            'd_min': [binner.bin_d_min(i+1) for i in range(n_rows)]}
    dataframe = pd.DataFrame(data).iloc[1:-1, :]
    dataframe.loc[dataframe['d_max'] < 0, 'd_max'] = np.Infinity
    return dataframe.reset_index()

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

  @property
  def n_bins(self) -> int:
    return self.parameters.statistics.n_bins

  @property
  def n_miller(self) -> int:
    return len(self.miller_arrays)

  # based on iotbx/command_line/reflection_statistics.py, lines 82-87
  def _evaluate_completeness(self) -> None:
    """Bin & evaluate completeness of each Miller array"""
    binned_datas = []
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      binned_datas.append(ma_without_absences.completeness(use_binning=True))
    return binned_datas

  def _evaluate_i_over_sigma(self) -> None:
    """Bin & evaluate I/sigma in each Miller array"""
    binned_datas = []
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      binned_datas.append(ma_without_absences.i_over_sig_i(use_binning=True))
    return binned_datas

  def _evaluate_r_factor(self) -> None:
    """Based heavily on xfel/command_line/riso.py by Iris Young. TODO: unify"""
    f_calc = self.miller_reference
    r_iso_calc = RIsoCalculator( anomalous_flag=False, d_min=self.d_min,
                                 d_max=self.d_max, n_bins=self.n_bins)
    binned_datas = []
    for ma in self.miller_arrays:
      f_obs = ma.as_amplitude_array()
      binned_datas.append(r_iso_calc.calculate(f_calc, f_obs))
    return binned_datas

  def evaluate(self):
    for stat in self.parameters.statistics.kind:
      method_name = EvaluatedStatistic.REGISTRY[stat].evaluate_method_name
      getattr(self, method_name)()


class MillerEvaluationArtist:
  """Visualise the `results` of MillerEvaluator based on passed `parameters`"""
  def __init__(self, me: MillerEvaluator) -> None:
    self.me: MillerEvaluator = me
    self.colormap = plt.get_cmap('tab10')
    self.colormap_period = 10
    self.figure, self.ax = plt.subplots()
    self.figure.set_size_inches(8., 6.)

  @property
  def color_list(self) -> List:
    """List of colors, each corresponding to different MillerEvaluator array"""
    return [self.colormap(i % self.colormap_period)
            for i in range(self.me.n_miller)]

  @property
  def x(self) -> list:
    return [1 + n_bin for n_bin in range(self.me.n_bins)]

  @property
  def x_lim(self):
    return min(self.x_ticks) - 0.1, max(self.x_ticks) + 0.1

  @property
  def x_ticks(self):
      return [0.5 + n_bin for n_bin in range(self.me.n_bins + 1)]

  @property
  def x_ticklabels(self) -> list:
    d_vals = [self.me.results['d_max'].iloc[0]] + list(self.me.results['d_min'])
    return ['{:.2f}'.format(round(d_val, 2)) for d_val in d_vals]

  def _visualize_as_line(self, stat_name: str) -> None:
    y_label = EvaluatedStatistic.REGISTRY[stat_name].full_name
    self.ax.set(xlabel='d_min [A]', xlim=self.x_lim, xticks=self.x_ticks,
                xticklabels=self.x_ticklabels, ylabel=y_label)
    for i in reversed(range(self.me.n_miller)):
      key = f'{stat_name}_{i}'
      y = self.me.results[key]
      self.ax.plot(self.x, y, color=self.color_list[i], label=f'mtz{i}')
    self.ax.legend(loc='upper right')

  def _visualize_completeness(self):
    self._visualize_as_line('cplt')

  def _visualize_i_over_sigma(self):
    self._visualize_as_line('I_over_si')

  def _visualize_r_factor(self):
    self._visualize_as_line('Riso')

  def visualize(self):
    for stat in self.me.parameters.statistics.kind:
      method_name = EvaluatedStatistic.REGISTRY[stat].visualize_method_name
      getattr(self, method_name)()
      self.figure.savefig(f'{stat}.png')
      self.ax.clear()


def run(params_):
  me = MillerEvaluator(parameters=params_)
  me.evaluate()
  print(me.results)
  mea = MillerEvaluationArtist(me=me)
  mea.visualize()


params = []
if __name__ == '__main__':
  params, options = parse_input()
  if '-h' in options or '--help' in options:
    print(message)
    exit()
  run(params)
