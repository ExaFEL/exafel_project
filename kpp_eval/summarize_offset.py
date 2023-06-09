from __future__ import division

from dataclasses import asdict, dataclass
import re
from typing import List

from exafel_project.kpp_eval.phil import parse_input, phil_scope_a

import numpy as np
import pandas as pd


message = """
This script produces a table summarizing the radial, transverse, and total
offset of reflection positions after multiple different processing approaches.
For the purpose of ExaFEL project, it aims to compare batch-wise offset
after DIALS and diffBragg stage1 refinement.

This is a work in progress.
""".strip()


@dataclass
class DetectorResiduals:
  """Storage for individual detector residuals output log values in micron"""
  corr_radial_psi: float
  corr_transverse_psi: float
  refls_count: int
  rmsd_overall_mean: float
  rmsd_overall_stddev: float
  rmsd_radial_mean: float
  rmsd_radial_stddev: float
  rmsd_transverse_mean: float
  rmsd_transverse_stddev: float
  d_max: float = np.inf
  d_min: float = 0.0

  TABLE_COLUMN_ORDER = ['d_max', 'd_min', 'refls_count',
                        'rmsd_overall_mean', 'rmsd_overall_stddev',
                        'rmsd_radial_mean', 'rmsd_radial_stddev',
                        'rmsd_transverse_mean', 'rmsd_transverse_stddev',
                        'corr_radial_psi', 'corr_transverse_psi']

  # These regexes match the contents of the detector residuals output table
  REFL_COUNT_REGEX = re.compile(r'(?<=\n) +\d+ +\d+\.\d+ +\d+\.\d+ +\d+\.\d+ '
                                r'+(\d+) +-?\d+% +-?\d+(?=%\n)')
  RMSD_MEAN_REGEX = re.compile(r'Weighted PG mean +(\d+.\d+) '
                               r'+(\d+.\d+) +(\d+.\d+) *(?=\n)')
  RMSD_STDDEV_REGEX = re.compile(r'Weighted PG stddev +(\d+.\d+) '
                                 r'+(\d+.\d+) +(\d+.\d+) *(?=\n)')
  MEAN_CORR_REGEX = re.compile(r'Refls Mean +(-?\d+)% +(-?\d+)%')

  @classmethod
  def from_log(cls, log_path: str) -> 'DetectorResiduals':
    log_text = open(log_path, 'r').read()
    refls_count = sum(int(n) for n in cls.REFL_COUNT_REGEX.findall(log_text))
    rmsd_means = cls.RMSD_MEAN_REGEX.search(log_text)
    rmsd_stddevs = cls.RMSD_STDDEV_REGEX.search(log_text)
    mean_correlations = cls.MEAN_CORR_REGEX.search(log_text)
    return cls(
      corr_radial_psi=mean_correlations[1],
      corr_transverse_psi=mean_correlations[2],
      refls_count=refls_count,
      rmsd_overall_mean=rmsd_means[1],
      rmsd_radial_mean=rmsd_means[2],
      rmsd_transverse_mean=rmsd_means[3],
      rmsd_overall_stddev=rmsd_stddevs[1],
      rmsd_radial_stddev=rmsd_stddevs[2],
      rmsd_transverse_stddev=rmsd_stddevs[3]
    )


def collect_offset_dataframe(parameters) -> pd.DataFrame:
  """For each input bin get DetectorResiduals, merge them all into DataFrame"""
  drs: List[DetectorResiduals] = []
  for bin_ in parameters.bin:
    dr = DetectorResiduals.from_log(bin_.path)
    dr.d_max = d if (d := bin_.d_max) and d >= 0 else np.inf
    dr.d_min = d if (d := bin_.d_min) and d >= 0 else 0.0
    drs.append(DetectorResiduals.from_log(bin_.path))
  df = pd.DataFrame.from_records([asdict(dr) for dr in drs])
  df = df[DetectorResiduals.TABLE_COLUMN_ORDER]
  return df


def run(params_) -> None:
  df = collect_offset_dataframe(parameters=params_)
  print(df)


params = []
if __name__ == '__main__':
  params, options = parse_input(phil_scope_a)
  if '-h' in options or '--help' in options:
    print(message)
    exit()
  run(params)
