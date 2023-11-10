"""
Read stage 1 pandas table and draw desired contents as histogram or heatmap.
"""

from collections import deque
import glob
from itertools import islice

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Generator, List, Sequence, Tuple, TypeAlias, TypeVar

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
stage1 = None
  .type = str
  .help = Directory with stage 1 results. If None, use current working dir.
x_key = sigz
  .type = str
  .help = Stage 1 results key to be visualized along x axis. Valid keys incl.:
  .help = 'a', 'a_init', 'al', 'al_init', 'b', 'b_init', 'be', 'be_init',
  .help = 'beamsize_mm', 'c', 'c_init', 'detz_shift_mm', 'eta', 'exp_idx',
  .help = 'fp_fdp_shift', 'ga', 'ga_init', 'lam0', 'lam1', 'niter', 'osc_deg',
  .help = 'oversample', 'phi_deg', 'rotX', 'rotY', 'rotZ', 'sigz', 
  .help = 'spot_scales', 'spot_scales_init', 'total_flux', and 'ncells_dist'.
y_key = ncells_dist
  .type = str
  .help = Stage 1 results key to be visualized along y axis. For a list
  .help = of available keys, refer to `x_key`'s help string.
"""

T = TypeVar('T')
Stage1Results: TypeAlias = pd.DataFrame


def sliding_pairs(sequence: Sequence[T]) -> Generator[Tuple[T]]:
    it = iter(sequence)
    window = deque(islice(it, 1), maxlen=2)
    for x in it:
        window.append(x)
        yield tuple(window)


def calculate_n_cells_dist(df: Stage1Results) -> Stage1Results:
    n_cells = np.array(list(df['ncells']))
    n_cells_init = np.array(list(df['ncells_init']))
    df['ncells_dist'] = np.sum((n_cells - n_cells_init) ** 2, axis=1) ** 0.5
    return df


def calculate_column_ranks(df: Stage1Results, key: str) -> Stage1Results:
    df[key + '_rank'] = df[key].rank(axis=0, method='first')
    return df


def plot_heatmap(df: Stage1Results, x_key: str, y_key: str) -> Stage1Results:
    n_bins = np.log2(len(df))
    x_lims = (min(df[x_key]), max(df[x_key]) + 1e-9)
    y_lims = (min(df[y_key]), max(df[y_key]) + 1e-9)
    x_bins_lims = np.linspace(x_lims[0], x_lims[1], num=n_bins+1)
    y_bins_lims = np.linspace(y_lims[0], y_lims[1], num=n_bins+1)
    heat_data = np.zeros(shape=(n_bins, n_bins), dtype=int)
    df['__x_bin'] = df['__y_bin'] = 0
    for x_bins_max in x_bins_lims[1:]:
        df['__x_bin'] += df[x_key] > x_bins_max
    for y_bins_max in y_bins_lims[1:]:
        df['__y_bin'] += df[y_key] > y_bins_max
    for x_i, x_bin_lims in enumerate(sliding_pairs(x_bins_lims)):
        for y_i, y_bins_lims in enumerate(sliding_pairs(y_bins_lims)):
            heat_data[x_i, y_i] = sum((df[x_key] == x_i) & (df[y_key] == y_i))
    x_bin_counts = heat_data.sum(axis=1)
    y_bin_counts = heat_data.sum(axis=0)
    fig, ((axx, axn), (axh, axy)) = plt.subplots(2, 2, sharex='True',
        sharey=True, width_ratios=[2, 1], height_ratios=[1, 2])
    axh.imshow(heat_data, cmap="Purples")
    # axh.grid(which="minor", color="w", linestyle='-', linewidth=3)
    axh.set_xticks(np.arange(n_bins + 1) - 0.5, labels=x_bins_lims)
    axh.set_yticks(np.arange(n_bins + 1) - 0.5, labels=y_bins_lims)
    axh.set_xlabel(x_key)
    axh.set_ylabel(y_key)
    purple = plt.get_cmap('Purples')(1.0)
    axx.bar(x=n_bins, height=x_bin_counts, width=1, color=purple)
    axy.hbar(x=n_bins, height=y_bin_counts, width=1, color=purple)
    plt.show()


def read_pickled_dataframes(stage1_path: str = '.') -> Stage1Results:
    pickle_glob = stage1_path + '/**/pandas/hopper_results_rank*.pkl'
    pickle_paths = glob.glob(pickle_glob, recursive=True)
    stage1_dfs: List[pd.DataFrame] = []
    for pickle_path in pickle_paths:
        with open(pickle_path, 'rb') as pickle_file:
            stage1_dfs.append(pd.read_pickle(pickle_file))
    return pd.concat(stage1_dfs, ignore_index=True)


def main(parameters) -> None:
    p = p if (p := parameters.stage1) else '.'
    stage1_df = read_pickled_dataframes(p)
    stage1_df = calculate_n_cells_dist(stage1_df)
    plot_heatmap(stage1_df, x_key=parameters.x_key, y_key=parameters.y_key)


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  main(params)