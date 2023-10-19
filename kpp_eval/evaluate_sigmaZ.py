"""
Extract information about sigmaZ mean from stage2 error file/files
and plot it/them as a function of iteration step number.
"""

from collections import defaultdict
import pathlib
import re
import string

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
err = None
  .type = str
  .multiple = True
  .help = Path to the err file after stage2 containing sigmaZ information.
labels = None
  .type = str
  .multiple = False
  .help = If given, split by commas and use to name plotted datasets;
  .help = For example `err=1.err, err=2.err, labels="A,B C"` will name
  .help = the datasets in table and on plot "A" & "B C" instead of "1" & "2".
title = None
  .type = str
  .help = If given, use it as plot title. See also "split_samples"
kpp_report = False
  .type = bool
  .help = If true, split entries based on label into several subplots,
  .help = increase font size.
"""

SIGMA_Z_REGEX = re.compile(r'^.+sigmaZ: mean=(.+), median=(.+)$', flags=re.M)


def run(parameters) -> None:
  sigma_z_means = defaultdict(list)
  for err_path in parameters.err:
    job_id = pathlib.Path(err_path).stem
    with open(err_path, 'r') as err_file:
      for line in err_file:
        if m := SIGMA_Z_REGEX.match(line):
          sigma_z_means[job_id].append(m.group(1))
  keys = l.split(',') if (l := parameters.labels) else sigma_z_means.keys()
  sigma_z_means_df = pd.DataFrame(sigma_z_means.values(), dtype=float, index=keys).T
  print(sigma_z_means_df)
  if parameters.kpp_report:
    samples = []
    y_min = np.nanquantile(sigma_z_means_df, 0.001) - 0.1
    y_max = np.nanquantile(sigma_z_means_df, 0.999) + 0.1
    for k in keys:
      if (s := k.split(maxsplit=1)[0]) not in samples:
        samples.append(s)
    fig, axes = plt.subplots(ncols=len(samples), sharey=True)
    fig.set_size_inches(15, 5)
    axes[0].set_ylabel('Mean sigma Z', fontsize=12)
    for i, (ax, sample) in enumerate(zip(axes, samples)):
      for key in sigma_z_means_df:
        if key.startswith(sample):
          ax.plot(key, data=sigma_z_means_df, label=key.split(maxsplit=1)[1])
      ax.tick_params(labelsize=12, labelleft=True)
      ax.set_title(string.ascii_lowercase[i] + ") " + sample, fontsize=14, pad=10)
      ax.set_xlabel('Stage 2 iteration', fontsize=12)
      ax.set_ylim(y_min, y_max)
      ax.xaxis.get_major_locator().set_params(integer=True)
      if len(sigma_z_means_df.keys()) > 1:
        ax.legend(prop={"size": 12}, loc='upper right')
      ax.grid()
  else:
    fig, ax = plt.subplots()
    for job_id in sigma_z_means_df:
      ax.plot(job_id, data=sigma_z_means_df, label=job_id)
    if t := parameters.title:
      ax.set_title(t)
    ax.set_xlabel('Stage 2 iteration')
    ax.set_ylabel('Mean sigma Z')
    ax.xaxis.get_major_locator().set_params(integer=True)
    if len(sigma_z_means_df.keys()) > 1:
      ax.legend()
    ax.grid()
  plt.show()


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)



