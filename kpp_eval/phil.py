# This is a legacy file, to be deleted or adapted in the future

from __future__ import absolute_import, division, print_function

import sys

from dials.util.options import ArgumentParser
from iotbx.phil import parse


phil_scope_a_str = """
processing
  .multiple = True
{
  name = None
    .type = str
    .help = Name of the processing with its resolution bins listed
  bin
    .multiple = True
  {
    path = None
      .type = str
      .help = Path to the detector residuals output log file
    d_max = None
      .type = float
      .help = Maximum value of d-spacing in this data bin, default=infinity
    d_min = 0.0
      .type = float
      .help = Minimum value of d-spacing in this data bin, default=0
  }
}
""".strip()
phil_scope_a = parse(phil_scope_a_str)


phil_scope_d_str = """
input {
  pdb = path/to/file.pdb
    .type = str
    .multiple = False
    .help = Path to the reference pdb file used as a target for mtz file(s)
  mtz = path/to/mtz.mtz
    .type = str
    .multiple = True
    .help = Path to the mtz file(s) to be evaluated against the pdb reference
  anomalous_flag = False
    .type = bool
    .help = Treat Bijvoet pairs as independent to see anomalous differences
  wavelength = 1.85
    .type = float
    .help = Wavelength at which data was collected
}
statistics {
  n_bins = 10
    .type = int
    .help = Number of resolution bins to be analysed
  kind = *cplt *I_over_si *Riso
    .type = choice(multi=True)
    .help = Types of tests to be performed on the input files
}
output {
  prefix = kpp_eval
    .type = str
    .help = String prefix of all output file names
}
""".strip()
phil_scope_d = parse(phil_scope_d_str)


def parse_input(phil_scope):
  import libtbx.load_env  # implicit import
  parser = ArgumentParser(
    usage=f"\n libtbx.python {sys.argv[0]}",
    phil=phil_scope,
    epilog="Compare mtz file quality")
  # Parse the command line. quick_parse is required for MPI compatibility
  params, options = parser.parse_args(show_diff_phil=True, quick_parse=True)
  return params, options
