"""
Read stage 1 pandas table and draw desired contents as histogram or heatmap.
"""

from collections import deque
import glob
from itertools import islice

from matplotlib.patches import Patch
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
    .help = 'exp_idx', 'fp_fdp_shift', 'ga', 'ga_init', 'lam0', 'lam1',
    .help = 'ncells[0-2]', 'ncells_def[0-2]', 'ncells_init[0-2]', 'niter', 
    .help = 'osc_deg', 'oversample', 'phi_deg', 'rotX', 'rotY', 'rotZ', 'sigz',
    .help = 'spot_scales', 'spot_scales_init', 'total_flux', and 'ncells_dist',
    .help = as well as their arithmetic combinations, i.e. 'ncells2 - ncells0'.
  log_scale = False
    .type = bool
    .help = If true, make the x axis log-scale on the produced plot
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
    .help = For a list of available keys, refer to `x.key`'s help string.
  log_scale = False
    .type = bool
    .help = If true, make the y axis log-scale on the produced plot
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for y axis.
    .help = If None, `stage1` from the outer scope will be used.
  }
r {
  key = (ncells0-ncells_init0)/ncells_init0
    .type = str
    .help = Key of the pandas stage 1 results table that should be visualized
    .help = as the brightness of red color.
    .help = For a list of available keys, refer to `x.key`'s help string.
  log_scale = False
    .type = bool
    .help = If true, make the color scale with value's log on the produced plot
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for red coloring.
    .help = If None, `stage1` from the outer scope will be used.
  }
g {
  key = (ncells1-ncells_init1)/ncells_init1
    .type = str
    .help = Key of the pandas stage 1 results table that should be visualized
    .help = as the brightness of green color.
    .help = For a list of available keys, refer to `x.key`'s help string.
  log_scale = False
    .type = bool
    .help = If true, make the color scale with value's log on the produced plot
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for green coloring.
    .help = If None, `stage1` from the outer scope will be used.
  }
b {
  key = (ncells2-ncells_init2)/ncells_init2
    .type = str
    .help = Key of the pandas stage 1 results table that should be visualized
    .help = as the brightness of blue color.
    .help = For a list of available keys, refer to `x.key`'s help string.
  log_scale = False
    .type = bool
    .help = If true, make the color scale with value's log on the produced plot
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for blue coloring.
    .help = If None, `stage1` from the outer scope will be used.
  }
"""

T = TypeVar('T')
Stage1Results = pd.DataFrame
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)


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


def normalize_array(a: np.ndarray) -> np.ndarray:
    """Return an array normalized to 0-1 range; preserve boolean values"""
    if np.issubdtype(a.dtype, bool):
        return a.astype(float)
    else:
        lim = (mn, mx) if (mn := min(a)) < (mx := max(a)) else (mn, mn + 1e-10)
        return (a - lim[0]) / (lim[1] - lim[0])


def normalize_colors(
        r: Sequence = None,
        g: Sequence = None,
        b: Sequence = None,
        ) -> Tuple[Sequence, Sequence, Sequence]:
    r_full = np.array([0.9, 0.0, 0.0])
    r_null = np.array([0.1, 0.0, 0.0])
    g_full = np.array([0.0, 0.9, 0.0])
    g_null = np.array([0.0, 0.1, 0.0])
    b_full = np.array([0.0, 0.0, 0.9])
    b_null = np.array([0.0, 0.0, 0.1])
    l = [len(v) for v in (r, g, b) if v is not None][0]
    r_norm = normalize_array(r) if r is not None else np.zeros(l, dtype=float)
    g_norm = normalize_array(g) if g is not None else np.zeros(l, dtype=float)
    b_norm = normalize_array(b) if b is not None else np.zeros(l, dtype=float)
    c = (np.outer(r_full, r_norm) + np.outer(r_null, 1 - r_norm) +
         np.outer(g_full, g_norm) + np.outer(g_null, 1 - g_norm) +
         np.outer(b_full, b_norm) + np.outer(b_null, 1 - b_norm)) / 1.0
    return c.T


def plot_heatmap(x: pd.Series,
                 y: pd.Series,
                 r: pd.Series = None,
                 g: pd.Series = None,
                 b: pd.Series = None,
                 bins: int = None) -> Stage1Results:
    # TODO: Allow log-scale, allow individual rgb colors via r, g, b parameters
    series = {k: v for k, v in zip('xyrgb', [x, y, r, g, b]) if v is not None}
    assert_same_length(series.values())
    for series_key, series_value in series:
        print(series_key + ': ' + series_value.name)
        series_value.name = series_key
    print(pd.concat([s.describe() for s in series], axis=1))
    x_name = x.name
    y_name = y.name
    color_names = [col.name if col is not None else '' for col in (r, g, b)]
    xa = np.array(x)
    ya = np.array(y)
    r = r if any(k is not None for k in (r, g, b)) else np.zeros_like(xa)
    r = np.log10(r) if r is not None and r.attrs['log_space'] else r
    g = np.log10(g) if g is not None and g.attrs['log_space'] else g
    b = np.log10(b) if b is not None and b.attrs['log_space'] else b
    c = normalize_colors(r, g, b)
    bins = bins if bins else int(np.log2(len(x)))
    x_space = np.linspace if x.attrs['log_space'] else np.logspace
    y_space = np.linspace if y.attrs['log_space'] else np.logspace
    x_bins = x_space(min(xa), max(xa), num=bins+1)
    y_bins = y_space(min(ya), max(ya), num=bins+1)
    heat = np.zeros(shape=(bins, bins), dtype=int)
    x_bin = np.zeros(len(xa), dtype=int)
    y_bin = np.zeros(len(ya), dtype=int)

    for x_bin_max in x_bins[1:-1]:
        x_bin += x > x_bin_max
    for y_bin_max in y_bins[1:-1]:
        y_bin += y > y_bin_max

    for x_i in range(bins):
        for y_i in range(bins):
            heat[x_i, y_i] = sum((x_bin == x_i) & (y_bin == y_i))
    x_colors = [np.mean(c[x_bin == x_i], axis=0) for x_i in range(bins)]
    y_colors = [np.mean(c[y_bin == y_i], axis=0) for y_i in range(bins)]

    fig, ((axx, axn), (axh, axy)) = plt.subplots(2, 2, sharex='col',
        sharey='row', width_ratios=[2, 1], height_ratios=[1, 2])
    plt.subplots_adjust(wspace=0, hspace=0)

    axh.axvline(x=xa.mean(), color='k')
    axh.axhline(y=ya.mean(), color='k')
    axh.set_aspect('auto')
    axh.scatter(x=xa, y=ya, c=c, s=10)
    axh.set_xlabel(x_name)
    axh.set_ylabel(y_name)
    axh.set_xlim(min(xa), max(xa))
    axh.set_ylim(min(ya), max(ya))
    axh.set_xscale('log' if x.attrs['log_scale'] else 'linear')
    axh.set_yscale('log' if y.attrs['log_scale'] else 'linear')

    axh.legend(handles=[Patch(color=color, label=label) for color, label
                        in zip('rgb', color_names) if color is not None])
    x_hist = axx.hist(xa, bins=x_bins, orientation='vertical')
    for bar, x_color in zip(x_hist[2], x_colors):
        bar.set_facecolor(x_color)
    y_hist = axy.hist(ya, bins=y_bins, orientation='horizontal')
    for bar, y_color in zip(y_hist[2], y_colors):
        bar.set_facecolor(y_color)
    axn.axis('off')
    ab = np.polyfit(xa, ya, deg=1)
    r = np.corrcoef(xa, ya)[0, 1]
    axn_text = f'a = {ab[0]:.2e}\nb = {ab[1]:.2e}\nR = {r:+6.4f}'
    axn.annotate(axn_text, xy=(.5, .5), xycoords='axes fraction',
                 ha='center', va='center')
    plt.show()


def prepare_series(parameters, default_path: str) -> pd.DataFrame:
    if parameters.key is None:
        return None
    path = p if (p := parameters.stage1) else default_path
    df = read_pickled_dataframes(path)
    df = calculate_n_cells_dist(df)
    df = split_tuple_columns(df)
    if (key := parameters.key) not in df:
        df[key] = df.eval(key)
    df.attrs['log_scale'] = parameters.logscale
    return pd.Series(df[key], name=path + ': ' + key)


def main(parameters) -> None:
    stage1_path = p if (p := parameters.stage1) else '.'
    x = prepare_series(parameters.x, stage1_path)
    y = prepare_series(parameters.y, stage1_path)
    r = prepare_series(parameters.r, stage1_path)
    g = prepare_series(parameters.g, stage1_path)
    b = prepare_series(parameters.b, stage1_path)
    plot_heatmap(x, y, r, g, b)


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  main(params)
