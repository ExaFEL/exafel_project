from __future__ import absolute_import, division, print_function

import argparse
import sys
from typing import Tuple, Union

from dials.util.options import ArgumentParser
from iotbx.phil import parse
from libtbx.phil import scope, scope_extract


def parse_phil(phil_scope: Union[str, scope]) -> \
    Tuple[scope_extract, argparse.Namespace]:
  """Parse phil scope or scope-describing string into parameters and options"""
  phil_scope = parse(phil_scope) if isinstance(phil_scope, str) else phil_scope
  import libtbx.load_env  # implicit import
  ap = ArgumentParser(usage=f"\n libtbx.python {sys.argv[0]}", phil=phil_scope)
  # Parse the command line. quick_parse is required for MPI compatibility
  params, options = ap.parse_args(show_diff_phil=True, quick_parse=True)
  return params, options
