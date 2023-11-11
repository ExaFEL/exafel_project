"""
Read stage 1 pandas table and draw desired contents as histogram or heatmap.
"""

from collections import deque
import glob
from itertools import islice

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Generator, List, Sequence, Tuple, TypeVar

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
stage1 = None
  .type = str
  .help = Directory with stage 1 results. If None, use current working dir.
x_key = sigz
  .type = str
  .help = Stage 1 results key to be visualized along x axis. Valid keys incl.:
  .help = 'Amats[0-8]', 'a', 'a_init', 'al', 'al_init',
  .help = 'b', 'b_init', 'be', 'be_init', 'beamsize_mm', 'c', 'c_init',
  .help = 'detz_shift_mm', 'diffuse_sigma[0-2]', 'eta', 'eta_abc[0-2]',
  .help = 'eta', 'exp_idx', 'fp_fdp_shift', 'ga', 'ga_init', 'lam0', 'lam1',
  .help = 'ncells[0-2]', 'ncells_def[0-2]', 'ncells_init[0-2]', 'niter', 
  .help = 'osc_deg', 'oversample', 'phi_deg', 'rotX', 'rotY', 'rotZ', 'sigz',
  .help = 'spot_scales', 'spot_scales_init', 'total_flux', and 'ncells_dist',
  .help = as well as their arithmetic combinations, i.e. 'ncells2 - ncells0'.
y_key = ncells_dist
  .type = str
  .help = Stage 1 results key to be visualized along y axis. For a list
  .help = of available keys, refer to `x_key`'s help string.
"""

T = TypeVar('T')
Stage1Results = pd.DataFrame


def sliding_pairs(sequence: Sequence[T]) -> Generator[Tuple[T], None, None]:
    it = iter(sequence)
    window = deque(islice(it, 1), maxlen=2)
    for x in it:
        window.append(x)
        yield tuple(window)


def assert_same_length(*args: Tuple[Sequence]) -> None:
    if (lens := {len(arg) for arg in args}) > 1:
        raise ValueError(f'Iterable input lengths do not match: {lens}')


def calculate_n_cells_dist(df: Stage1Results) -> Stage1Results:
    n_cells = np.array(list(df['ncells']))
    n_cells_init = np.array(list(df['ncells_init']))
    df['ncells_dist'] = np.sum((n_cells - n_cells_init) ** 2, axis=1) ** 0.5
    return df


def calculate_column_ranks(df: Stage1Results, key: str) -> Stage1Results:
    df[key + '_rank'] = df[key].rank(axis=0, method='first')
    return df


def split_tuple_columns(df: Stage1Results):
    """In `df`, for each `df` column `key` containing tuples of length N,
    split the tuples into new columns `key0`, `key1`,... `keyN-1`."""
    splittable = [k for k in df.keys() if isinstance(v := df[k][0], tuple)]
    for s in splittable:
        split = [s + str(i) for i in range(len(df[s][0]))]
        df[split] = pd.DataFrame(df[s].tolist(), index=df.index)
    return df


def plot_heatmap(x: pd.Series,
                 y: pd.Series,
                 bins: int = None) -> Stage1Results:
    # TODO: Allow log-scale, allow individual rgb colors via r, g, b parameters
    assert_same_length(x, y)
    x = np.array(x)
    y = np.array(y)
    bins = bins if bins else int(np.log2(len(x)))
    x_lims = np.linspace(min(x), max(x) + 1e-9, num=bins+1)
    y_lims = np.linspace(min(y), max(y) + 1e-9, num=bins+1)
    heat = np.zeros(shape=(bins, bins), dtype=int)
    x_bin = np.zeros(len(x), dtype=int)
    y_bin = np.zeros(len(y), dtype=int)

    for x_bin_max in x_lims[1:]:
        x_bin += x > x_bin_max
    for y_bin_max in y_lims[1:]:
        y_bin += x > y_bin_max

    for x_i in range(len(x)):
        for y_i in range(len(y)):
            heat[x_i, y_i] = sum((x_bin == x_i) & (y_bin == y_i))
    heat_x = heat.sum(axis=0)
    heat_y = heat.sum(axis=1)

    fig, ((axx, axn), (axh, axy)) = plt.subplots(2, 2, sharex='col',
        sharey='row', width_ratios=[2, 1], height_ratios=[1, 2])
    plt.subplots_adjust(wspace=0, hspace=0)

    axh.imshow(heat, cmap="Purples", origin='lower')
    axh.set_aspect('auto')
    x_tick_labels = ["{:.2E}".format(t) for t in x_lims]
    y_tick_labels = ["{:.2E}".format(t) for t in y_lims]
    axh.set_xticks(np.arange(len(x) + 1) - 0.5, labels=x_tick_labels)
    axh.set_yticks(np.arange(len(y) + 1) - 0.5, labels=y_tick_labels)
    for data, set_label in [(x, axh.set_xlabel), (y, axh.set_ylabel)]:
        if hasattr(data, 'name') and data.name:
            set_label(data.name)
    purple = plt.get_cmap('Purples')(1.0)
    axh.scatter(x=x/len(x), y=y/len(y), color='#000000')
    axx.bar(x=range(bins), height=heat_x, width=1, color=purple)
    axy.barh(y=range(bins), width=heat_y, height=1, color=purple)
    axn.axis('off')
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
    stage1_df = split_tuple_columns(stage1_df)
    if (x_key := parameters.x_key) not in stage1_df:
        stage1_df[x_key] = stage1_df.eval(x_key)
    if (y_key := parameters.y_key) not in stage1_df:
        stage1_df[y_key] = stage1_df.eval(y_key)
    plot_heatmap(x=stage1_df[x_key], y=stage1_df[y_key])


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  main(params)
