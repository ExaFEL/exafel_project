from __future__ import absolute_import, division, print_function

import sys

from dials.util.options import ArgumentParser
from iotbx.phil import parse


MASTER_PHIL = """
input {
  pdb = path/to/file.pdb
    .type = str
    .multiple = False
    .help = Path to the reference pdb file used as a target for mtz file(s)
  mtz = path/to/mtz.mtz
    .type = str
    .multiple = True
    .help = Path to the mtz file(s) to be evaluated against the pdb reference
}
statistics {
  n_bins = 10
    .type = int
    .help = Number of resolution bins to be analysed
  kind = cplt I/si R
    .type = choice
    .multiple = True
    .help = Types of tests to be performed on the input files
}
output {
  prefix = kpp_eval
    .type = str
    .help = String prefix of all output file names
}
"""


def parse_input():
  phil_scope = parse(MASTER_PHIL)
  import libtbx.load_env  # implicit import
  parser = ArgumentParser(
    usage=f"\n libtbx.python {sys.argv[0]}",
    phil=phil_scope,
    epilog="Compare mtz file quality")
  # Parse the command line. quick_parse is required for MPI compatibility
  params, options = parser.parse_args(show_diff_phil=True, quick_parse=True)
  return params, options
