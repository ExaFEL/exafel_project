from __future__ import division

import functools
from typing import Callable, List, Tuple

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


miller_statistic_evaluator_map = dict()
miller_evaluator_statistic_map = dict()
miller_statistic_visualizer_map = dict()


def evaluator_of(statistic_name: str) -> Callable:
  """Evaluate decorator factory which assigns eval methods to statistics"""
  def evaluate_decorator(_evaluate_method: Callable) -> Callable:
    """Decorator for MillerEvaluator which auto-registers evaluation results"""
    miller_statistic_evaluator_map[statistic_name] = _evaluate_method.__name__
    miller_evaluator_statistic_map[_evaluate_method.__name__] = statistic_name

    @functools.wraps(_evaluate_method)
    def _evaluate_method_wrapper(self: 'MillerEvaluator', *args, **kwargs):
      stat_name = miller_evaluator_statistic_map[_evaluate_method.__name__]
      binned_datas = _evaluate_method(self, *args, **kwargs)
      for i, binned_data in enumerate(binned_datas):
        self.results[f'{stat_name}_{i}'] = binned_data.data[1:-1]
      return binned_datas
    return _evaluate_method_wrapper
  return evaluate_decorator


def visualizer_of(statistic_name: str) -> Callable:
  """Evaluate decorator factory which assigns eval methods to statistics"""
  def visualize_decorator(_visualize_method: Callable) -> Callable:
    """Decorator for MillerEvaluator which auto-registers visualize methods"""
    miller_statistic_visualizer_map[statistic_name] = _visualize_method.__name__

    @functools.wraps(_visualize_method)
    def _visualize_method_wrapper(self: 'MillerEvaluator', *args, **kwargs):
      return _visualize_method(self, *args, **kwargs)
    return _visualize_method_wrapper
  return visualize_decorator


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
  @evaluator_of('cplt')
  def _evaluate_completeness(self) -> None:
    """Bin & evaluate completeness of each Miller array"""
    binned_datas = []
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      binned_datas.append(ma_without_absences.completeness(use_binning=True))
    return binned_datas

  @evaluator_of('I_over_si')
  def _evaluate_i_over_sigma(self) -> None:
    """Bin & evaluate I/sigma in each Miller array"""
    binned_datas = []
    for ma in self.miller_arrays:
      ma_without_absences = ma.eliminate_sys_absent()
      binned_datas.append(ma_without_absences.i_over_sig_i(use_binning=True))
    return binned_datas

  @evaluator_of('Riso')
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
    for statistic in self.parameters.statistics.kind:
      getattr(self, miller_statistic_evaluator_map[statistic])()


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
  def x_tics(self):
      return [0.5 + n_bin for n_bin in range(self.me.n_bins + 1)]

  @property
  def x_ticklabels(self) -> list:
    d_min = d0 if (d0 := self.me.results['d_min'].iloc[0]) else np.Infinity
    return [d_min] + list(self.me.results['d_max'])

  def setup_axes(self):
    self.ax.set(xlabel='d_min [A]', xticks=self.x_tics)

  def _visualize_as_line(self, stat_name: str) -> None:
    self.ax.set(title=stat_name)
    for i in reversed(range(self.me.n_miller)):
      key = f'{stat_name}_{i}'
      y = self.me.results[key]
      self.ax.plot(self.x, y, color=self.color_list[i], label=f'mtz{i}')

  @visualizer_of('cplt')
  def _visualize_completeness(self):
    self._visualize_as_line('cplt')

  @visualizer_of('I_over_si')
  def _visualize_i_over_sigma(self):
    self._visualize_as_line('I_over_si')

  @visualizer_of('Riso')
  def _visualize_r_factor(self):
    self._visualize_as_line('Riso')

  def visualize(self):
    for stat_name in self.me.parameters.statistics.kind:
      self.setup_axes()
      getattr(self, miller_statistic_visualizer_map[stat_name])()
      self.figure.savefig(f'{stat_name}.png')
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
