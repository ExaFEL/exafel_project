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
  .help = Directory with stage 1 results. If None, look recursively in work dir.
x {
  key = sigz
    .type = str
    .help = Key of the pandas stage 1 results table that should be visualized
    .help = along the x axis. Valid keys include:
    .help = 'Amats[0-8]', 'a', 'a_init', 'al', 'al_init',
    .help = 'b', 'b_init', 'be', 'be_init', 'beamsize_mm', 'c', 'c_init',
    .help = 'detz_shift_mm', 'diffuse_sigma[0-2]', 'eta', 'eta_abc[0-2]',
    .help = 'eta', 'exp_idx', 'fp_fdp_shift', 'ga', 'ga_init', 'lam0', 'lam1',
    .help = 'ncells[0-2]', 'ncells_def[0-2]', 'ncells_init[0-2]', 'niter', 
    .help = 'osc_deg', 'oversample', 'phi_deg', 'rotX', 'rotY', 'rotZ', 'sigz',
    .help = 'spot_scales', 'spot_scales_init', 'total_flux', and 'ncells_dist',
    .help = as well as their arithmetic combinations, i.e. 'ncells2 - ncells0'.
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for x axis.
    .help = If None, `stage1` from the outer scope will be used.
  }
y {
  key = sigz
    .type = str
    .help = Key of the pandas stage 1 results table that should be visualized
    .help = along the y axis.
    .help = For a list of avaliable keys, refer to `x.key`'s help string.
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for y axis.
    .help = If None, `stage1` from the outer scope will be used.
  }
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
    if (lens := len({len(arg) for arg in args})) > 1:
        raise ValueError(f'Iterable input lengths do not match: {lens}')


def read_pickled_dataframes(stage1_path: str = '.') -> Stage1Results:
    pickle_glob = stage1_path + '/**/pandas/hopper_results_rank*.pkl'
    pickle_paths = glob.glob(pickle_glob, recursive=True)
    stage1_dfs: List[pd.DataFrame] = []
    for pickle_path in pickle_paths:
        with open(pickle_path, 'rb') as pickle_file:
            stage1_dfs.append(pd.read_pickle(pickle_file))
    df = pd.concat(stage1_dfs, ignore_index=True)
    df['exp_name+exp_idx'] = df['exp_name'] + df['exp_idx'].astype(str)
    df.sort_values(by='exp_name+exp_idx', inplace=True)
    return df


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
    splittable_keys = [k for k in df.keys() if isinstance(df[k][0], tuple)]
    for sk in splittable_keys:
        split_keys = [sk + str(i) for i in range(len(df[sk][0]))]
        df[split_keys] = pd.DataFrame(df[sk].tolist(), index=df.index)
    return df

def plot_heatmap(x: pd.Series,
                 y: pd.Series,
                 bins: int = None) -> Stage1Results:
    # TODO: Allow log-scale, allow individual rgb colors via r, g, b parameters
    assert_same_length(x, y)
    print(x.describe())
    print(y.describe())
    x_name = x.name
    y_name = y.name
    x = np.array(x)
    y = np.array(y)
    bins = bins if bins else int(np.log2(len(x)))
    x_bins = np.linspace(min(x), max(x), num=bins+1)
    y_bins = np.linspace(min(y), max(y), num=bins+1)
    heat = np.zeros(shape=(bins, bins), dtype=int)
    x_bin = np.zeros(len(x), dtype=int)
    y_bin = np.zeros(len(y), dtype=int)

    for x_bin_max in x_bins[1:-1]:
        x_bin += x > x_bin_max
    for y_bin_max in y_bins[1:-1]:
        y_bin += y > y_bin_max

    for x_i in range(bins):
        for y_i in range(bins):
            heat[x_i, y_i] = sum((x_bin == x_i) & (y_bin == y_i))

    fig, ((axx, axn), (axh, axy)) = plt.subplots(2, 2, sharex='col',
        sharey='row', width_ratios=[2, 1], height_ratios=[1, 2])
    plt.subplots_adjust(wspace=0, hspace=0)
    purple = plt.get_cmap('Purples')(1.0)

    axh_extent = (x_bins[0], x_bins[-1], y_bins[0], y_bins[-1])
    axh.imshow(heat.T, cmap="Purples", extent=axh_extent, origin='lower')
    axh.axvline(x=x.mean(), color=purple)
    axh.axhline(y=y.mean(), color=purple)
    axh.set_aspect('auto')
    axh.scatter(x=x, y=y, color='#008000', s=10)
    axh.set_xlabel(x_name)
    axh.set_ylabel(y_name)
    axx.hist(x, bins=x_bins, color=purple, orientation='vertical')
    axy.hist(y, bins=y_bins, color=purple, orientation='horizontal')
    axn.axis('off')
    ab = np.polyfit(x, y, deg=1)
    r = np.corrcoef(x, y)[0, 1]
    axn_text = f'a = {ab[0]:.2e}\nb = {ab[1]:.2e}\nR = {r:+6.4f}'
    axn.annotate(axn_text, xy=(.5, .5), xycoords='axes fraction',
                 ha='center', va='center')
    plt.show()


def main(parameters) -> None:
    stage1_path = p if (p := parameters.stage1) else '.'
    stage1_path_x = px if (px := parameters.x.stage1) else stage1_path
    stage1_path_y = py if (py := parameters.y.stage1) else stage1_path
    x_df = read_pickled_dataframes(stage1_path_x)
    x_df = calculate_n_cells_dist(x_df)
    x_df = split_tuple_columns(x_df)
    if (x_key := parameters.x.key) not in x_df:
        x_df[x_key] = x_df.eval(x_key)
    x = pd.Series(x_df[x_key], name=px + ': ' + x_key)
    y_df = read_pickled_dataframes(stage1_path_y)
    y_df = calculate_n_cells_dist(y_df)
    y_df = split_tuple_columns(y_df)
    if (y_key := parameters.y.key) not in y_df:
        y_df[y_key] = y_df.eval(y_key)
    y = pd.Series(y_df[x_key], name=py + ': ' + y_key)
    plot_heatmap(x, y)


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  main(params)
