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
plot {
  x_min = 0.
    .type = float
    .help = Minimum of x range to be plotted
  x_max = 50.
    .type = float
    .help = Maximum of x range to be plotted
}
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
  STATS_PERCENTILES = [1 - 0.1 ** n for n in range(1, 7)]

  def __init__(self, data: Sequence) -> None:
    self.data = data

  def __sub__(self, other) -> 'PixelArray':
    return self.__class__(self.data - other.data)

  def __abs__(self) -> 'PixelArray':
    return PixelArray(np.absolute(self.data))

  def __str__(self) -> str:
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
    return pd.Series(self.data).describe(percentiles=[.9, .99, .999, .9999])

def summarize_pixel_convergence(parameters) -> None:
  arrays = [PixelArray.from_h5(h5_path) for h5_path in parameters.h5]
  deltas = [abs(pa2 - pa1) for pa1, pa2 in zip(arrays[1:], arrays[:-1])]
  colors = plt.get_cmap('viridis')(np.linspace(0., 1., len(deltas) + 2)[1:-1])
  stats = [delta.stats() for delta in deltas]
  print(pd.concat(stats, axis=1))
  fig = plt.figure()
  ax = fig.add_subplot(111)
  ax.set_yscale('log')
  for i, delta in enumerate(deltas):
    label = f"{stats[i]['mean']:6.2f} +/- {stats[i]['std']:6.2f}"
    delta.plot_distribution(axes=ax, color=colors[i], label=label)
  plt.xlim(parameters.plot.x_min, parameters.plot.x_max)
  plt.legend()
  plt.show()

def run(params_):
  summarize_pixel_convergence(params_)


params = []
if __name__ == '__main__':
  params, options = parse_input()
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
