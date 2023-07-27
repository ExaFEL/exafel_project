"""
This python script accepts an N-length list of h5 files and returns a summary
of the evolution of pixel deltas between every pair of subsequent files.
"""

import sys
from typing import Sequence

from dials.util.options import ArgumentParser
from dxtbx.imageset import ImageSetFactory
from dxtbx.model.experiment_list import ExperimentListFactory
from iotbx.phil import parse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


phil_scope_str = """
h5 = None
  .type = str
  .multiple = True
  .help = Ordered paths to the h5 files to be compared against each other.
"""
phil_scope = parse(phil_scope_str)


def parse_input():
  import libtbx.load_env  # implicit import
  parser = ArgumentParser(
    usage=f"\n libtbx.python {sys.argv[0]}",
    phil=phil_scope,
    epilog="Calculate cross-correlation")
  # Parse the command line. quick_parse is required for MPI compatibility
  params_, options_ = parser.parse_args(show_diff_phil=True, quick_parse=True)
  return params_, options_


class PixelArray:
  def __init__(self, data: Sequence) -> None:
    self.data = data

  def __sub__(self, other) -> 'PixelArray':
    return self.__class__(self.data - other.data)

  def __abs__(self):
    return PixelArray(np.absolute(self.data))

  def __str__(self):
    return f'{self.__class__!s}({self.data!s})'

  @classmethod
  def from_h5(cls, h5_path: str) -> 'PixelArray':
    expts = ExperimentListFactory.from_filenames([h5_path], load_models=False)
    imageset = ImageSetFactory.imageset_from_anyset(expts[0].imageset)
    return cls(imageset.get_raw_data(0))

  @property
  def data(self) -> np.ndarray:
    return self._data

  @data.setter
  def data(self, value: Sequence) -> None:
    self._data = np.array(value).flatten()

  def plot_distribution(self,
                        axes: plt.Axes = None,
                        color: np.ndarray = 'r',
                        label: str = None,
                        ) -> None:
    axes = axes if axes else plt.gca()
    values, counts = np.unique(self.data, return_counts=True)
    x = np.array(range(min(values), max(values) + 1, 1))
    y = np.zeros_like(x)
    y[values-min(values)] = counts
    axes.step(x, y, where='mid', color=color, label=label)

  def stats(self) -> pd.DataFrame:
    return pd.DataFrame(self.data).describe()

def summarize_pixel_convergence(h5_paths: Sequence[str]) -> None:
  arrays = [PixelArray.from_h5(h5_path) for h5_path in h5_paths]
  deltas = [abs(pa2 - pa1) for pa1, pa2 in zip(arrays[1:], arrays[:-1])]
  colors = plt.get_cmap('viridis')(np.linspace(0.0, 1.0, len(deltas)+2)[1:-1])
  fig = plt.figure()
  ax = fig.add_subplot(111)
  for i, delta in enumerate(deltas):
    stats = delta.stats()
    label = f"{stats['mean']:6.2f} +/- {stats['std']:6.2f}"
    delta.plot_distribution(axes=ax, color=colors[i], label=label)
  plt.plot()

def run(params_):
  summarize_pixel_convergence(h5_paths=params_.h5)


params = []
if __name__ == '__main__':
  params, options = parse_input()
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
