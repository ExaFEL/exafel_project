from __future__ import absolute_import, division, print_function
import sys

def parse_input():
  from iotbx.phil import parse
  master_phil="""
    logger {
      outdir = .
        .type = path
        .help = Use "/mnt/bb/${USER}" for Summit NVME burst buffer
    }
    context = *kokkos_gpu kokkos_cpu cuda
      .type = choice
      .help = backend for parallel execution
    noise = True
      .type = bool
    psf = True
      .type = bool
    attenuation = True
      .type = bool
    beam {
      mean_wavelength = None
        .type = float
        .optional = False
        .help = spectra from big data are coerced to this mean wavelength
      total_flux = 1E12
        .type = float
        .help = spectra from big data are coerced to this total flux
    }
  """
  phil_scope = parse(master_phil)
  # The script usage
  import libtbx.load_env # implicit import
  from dials.util.options import ArgumentParser
  # Create the parser
  parser = ArgumentParser(
        usage="\n libtbx.python %s context=[kokkos_gpu|cuda]"%(sys.argv[0]),
        phil=phil_scope,
        epilog="test exafel API, cuda vs. kokkos")
  # Parse the command line. quick_parse is required for MPI compatibility
  params, options = parser.parse_args(show_diff_phil=True,quick_parse=True)
  return params,options
