"""
Read stage 1 pandas table and draw desired contents on a double histogram.
"""
import copy
from functools import lru_cache
from collections import deque
import glob
from itertools import islice
from numbers import Number

from matplotlib.patches import Patch, Rectangle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Generator, List, Sequence, Tuple, TypeVar

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
stage1 = None
  .type = str
  .help = Directory with stage 1 results. If None, look recursively in work dir.
heat = False
  .type = bool
  .help = If True, represent all data using a 2D heatmap instead of individual
  .help = points, which might represent voluminous data better. 2D heat is
  .help = drawn as a sqrt of point count in each bin with opacity. It can be
  .help = confused with brightness, so avoid using it alongside continuous rgb.
n_bins = None
  .type = int
  .help = Number of bins to group data along x and y. Default log2(len(x)).
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
    .help = 'spot_scales', 'spot_scales_init', 'total_flux'.
    .help = Additionally, for all columns that have an `_init` defined,
    .help = a distance to init is calculated, i.e. 'ncells_dist' or `c_dist`.
    .help = Arithmetic combinations are also allowed, i.e. 'ncells2 - ncells0'.
  log_scale = False
    .type = bool
    .help = If true, make the x axis log-scale on the produced plot
  stage1 = None
    .type = str
    .help = Directory with stage 1 results to be used for x axis.
    .help = If None, `stage1` from the outer scope will be used.
  tukey_limit = None
    .type = float
    .help = If given, don't plot Tukey outliers above `tukey_limit * iqr`.
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
  tukey_limit = None
    .type = float
    .help = If given, don't plot Tukey outliers above `tukey_limit * iqr`.
  }
r {
  key = ncells_dist0/ncells_init0
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
  tukey_limit = None
    .type = float
    .help = If given, don't plot Tukey outliers above `tukey_limit * iqr`.
  }
g {
  key = ncells_dist1/ncells_init1
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
  tukey_limit = None
    .type = float
    .help = If given, don't plot Tukey outliers above `tukey_limit * iqr`.
  }
b {
  key = ncells_dist2/ncells_init2
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
  tukey_limit = None
    .type = float
    .help = If given, don't plot Tukey outliers above `tukey_limit * iqr`.
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


def calculate_dist_columns(df: Stage1Results) -> Stage1Results:
    """Calculate distance to init for all cols with relevant `_init` defined.
    For cols of tuples, this is second norm, i.e. for `ncells=Series([(5,5,5)])`
    and `ncells_init=Series([(4,4,4)])` it adds `ncells_dist=Series([(3,3,3)])`.
    For cols of numeric, this is a signed difference, i.e. for `a=Series([6,9])`
    and `a_init=Series([8,8])`, it adds a column `a_dist=Series([-2,1])`."""
    cols_with_init = {k: k_init for k_init in df if '_init' in k_init and
                      ((k := k_init.replace('_init', '')) in df)}
    for cwi_key, cwi_init_key in cols_with_init.items():
        cwi = np.array(list(df[cwi_key]))
        cwi_init = np.array(list(df[cwi_init_key]))
        dist_key = cwi_init_key.replace('_init', '_dist')
        if isinstance(df[cwi_key][0], Number):
           df[dist_key] = cwi - cwi_init
        elif isinstance(df[cwi_key][0], tuple):
            df[dist_key] = np.sum((cwi - cwi_init) ** 2, axis=1) ** 0.5
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
    """Generate color for each point based on relative values of rgb series"""
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


def exclude_tukey_outliers(*series: pd.Series) -> Tuple[pd.Series]:
    """Exclude all points outside `[q1-tukey_limit*iqr, q3+tukey_limit*iqr]`"""
    outlier_mask = np.zeros_like(series[0], dtype=bool)
    limited_series = [s for s in series if s is not None and
                      s.attrs.get('tukey_limit', None)]
    for s in limited_series:
        quartiles = list(s.quantile([0.0, 0.25, 0.5, 0.75, 1.0]))
        iqr = quartiles[3] - quartiles[1]
        lim0 = quartiles[1] - (iqr * s.attrs.get('tukey_limit'))
        lim1 = quartiles[3] + (iqr * s.attrs.get('tukey_limit'))
        om = ((s < lim0) | (s > lim1)).values
        print(f'Skipping{sum(om):7d} points on plot: outliers in "{s.name}"')
        outlier_mask |= om
    if any(outlier_mask):
        print(f'Skipping{sum(outlier_mask):7d} points on plot in total.')
    return tuple(s if s is None else s[~outlier_mask] for s in series)


def plot_heatmap(x: pd.Series,
                 y: pd.Series,
                 r: pd.Series = None,
                 g: pd.Series = None,
                 b: pd.Series = None,
                 bins: int = None,
                 heat: bool = False) -> None:
    x_is_log = x is not None and x.attrs.get('log_scale', False)
    y_is_log = y is not None and y.attrs.get('log_scale', False)
    r_is_log = r is not None and r.attrs.get('log_scale', False)
    g_is_log = g is not None and g.attrs.get('log_scale', False)
    b_is_log = b is not None and b.attrs.get('log_scale', False)
    are_log = (x_is_log, y_is_log, r_is_log, g_is_log, b_is_log)

    series = {k: copy.deepcopy(v) for k, v in zip('xyrgb', [x, y, r, g, b])
              if v is not None}
    assert_same_length(series.values())
    for (sk, sv), ls in zip(series.items(), are_log):
        print(f'{sk}: "{sv.name}"' + f' (log)' * int(ls))
        sv.name = sk
    print(pd.concat([s.describe() for s in series.values()], axis=1))
    (x, y, r, g, b,) = exclude_tukey_outliers(x, y, r, g, b)  # noqa

    x_name = x.name
    y_name = y.name
    color_names = [col.name if col is not None else '' for col in (r, g, b)]
    xa = np.array(x)
    ya = np.array(y)
    r = r if any(k is not None for k in (r, g, b)) else np.zeros_like(xa)
    r = np.log10(r) if r_is_log else r
    g = np.log10(g) if g_is_log else g
    b = np.log10(b) if b_is_log else b
    c = normalize_colors(r, g, b)
    bins = bins if bins else int(np.log2(len(x)))
    x_space = np.geomspace if x_is_log else np.linspace
    y_space = np.geomspace if y_is_log else np.linspace
    x_bins = x_space(min(xa), max(xa), num=bins+1)
    y_bins = y_space(min(ya), max(ya), num=bins+1)
    x_bin_idx = np.digitize(xa, x_bins, right=True) - 1  # in digitize, 0 = out
    y_bin_idx = np.digitize(ya, y_bins, right=True) - 1  # in digitize, 0 = out
    x_colors = [np.mean(c[x_bin_idx == x_i], axis=0) for x_i in range(bins)]
    y_colors = [np.mean(c[y_bin_idx == y_i], axis=0) for y_i in range(bins)]

    fig, ((axx, axn), (axh, axy)) = plt.subplots(2, 2, sharex='col',
        sharey='row', width_ratios=[2, 1], height_ratios=[1, 2])
    plt.subplots_adjust(wspace=0, hspace=0)

    if heat:
        xy_heat = np.zeros(shape=(bins, bins, 4), dtype=float)
        for x_i in range(bins):
            for y_i in range(bins):
                mask = (x_bin_idx == x_i) & (y_bin_idx == y_i)
                xy_heat[x_i, y_i, 3] = (sum_ := np.sum(mask))
                xy_heat[x_i, y_i, :3] = c[mask].mean(axis=0) if sum_ else 0.
        xy_heat[:, :, 3] /= np.max(xy_heat[:, :, 3])
        xy_heat[:, :, 3] **= 0.5  # use square root to emphasize smaller bins
        for x_i in range(bins):
            for y_i in range(bins):
                rect_s = (x_bins[x_i], y_bins[y_i])
                rect_w = x_bins[x_i+1] - x_bins[x_i]
                rect_h = y_bins[y_i+1] - y_bins[y_i]
                axh.add_patch(Rectangle(rect_s, rect_w, rect_h, ec=None,
                                        color=xy_heat[x_i, y_i, :]))
    else:
        axh.scatter(x=xa, y=ya, c=c, s=10, marker='.')

    axh.axvline(x=xa.mean(), color='k')
    axh.axhline(y=ya.mean(), color='k')
    axh.set_aspect('auto')

    axh.set_xlabel(x_name)
    axh.set_ylabel(y_name)
    axh.set_xlim(min(xa), max(xa))
    axh.set_ylim(min(ya), max(ya))
    axh.set_xscale('log' if x_is_log else 'linear')
    axh.set_yscale('log' if y_is_log else 'linear')

    if any(c is not None for c in (r, g, b)):
        axh.legend(handles=[Patch(color=color, label=label) for color, label
                            in zip('rgb', color_names) if label])
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


@lru_cache(maxsize=5)
def prepare_dataframe(path: str) -> pd.DataFrame:
    df = read_pickled_dataframes(path)
    df = split_tuple_columns(df)
    df = calculate_dist_columns(df)
    return df


def prepare_series(parameters, default_path: str) -> pd.DataFrame:
    if parameters.key is None:
        return None
    path = p if (p := parameters.stage1) else default_path
    df = prepare_dataframe(path)
    if (key := parameters.key) not in df:
        df[key] = df.eval(key)
    series = pd.Series(df[key], name=path + ': ' + key)
    series.attrs['log_scale'] = parameters.log_scale
    series.attrs['tukey_limit'] = parameters.tukey_limit
    return series


def main(parameters) -> None:
    stage1_path = p if (p := parameters.stage1) else '.'
    x = prepare_series(parameters.x, stage1_path)
    y = prepare_series(parameters.y, stage1_path)
    r = prepare_series(parameters.r, stage1_path)
    g = prepare_series(parameters.g, stage1_path)
    b = prepare_series(parameters.b, stage1_path)
    plot_heatmap(x, y, r, g, b, bins=parameters.n_bins, heat=parameters.heat)


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  main(params)
