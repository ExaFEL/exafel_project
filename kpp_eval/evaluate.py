from __future__ import division

from dataclasses import dataclass
import glob
from typing import List
import sys

from iotbx import reflection_file_reader
from kpp_eval.phil import parse_input
from LS49.sim.util_fmodel import gen_fmodel

from mpl_toolkits.mplot3d import Axes3D  # noqa: required to use 3D axes
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import scipy as sp


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


class MTZFileEvaluator:
  def __init__(self, parameters):
    self.parameters = parameters
    self.mtz: list = self.read_mtz()
    self.ref = self.read_pdb()

  def read_mtz(self):
    mtz_objects = []
    for mtz_path in self.parameters.input.mtz:
      mtz = reflection_file_reader.any_reflection_file(file_name=mtz_path)
      mtz_objects.append(mtz)
    return mtz_objects

  def read_pdb(self):
    pdb_lines = open(self.parameters.input.pdb, "r").read()
    model = gen_fmodel(resolution=2.5,
                       pdb_text=pdb_lines,
                       algorithm="fft", wavelength=1.54)
    return model


def run(params_):
  ev = MTZFileEvaluator(parameters=params_)
  print(f'{type(ev.ref)=}')
  for mtz in ev.mtz:
    print(f'{type(mtz)=}')


params = []
if __name__ == '__main__':
  params, options = parse_input()  # test how to use this reader correctly
  if '-h' in options or '--help' in options:
    print(message)
    exit()
  run(params)
