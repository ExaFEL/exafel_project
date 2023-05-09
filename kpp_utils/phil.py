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
    crystal {
      structure = *ferredoxin PSII
        .type = choice
        .help = type of crystal structure to be simulated
    }
    detector {
      tiles = *single multipanel
        .type = choice
        .help = use fundamentally different function calls for single panel or multipanel detectors
      reference = None
        .type = path
        .help = give the *.expt file to serve as reference for both beam and detector
    }
    output {
      format = *smv cbf h5 h5_stage1
        .type = choice
        .help = smv: super marty view ADSC format for NESAP benchmark with gzip
        .help = cbf: not really tested
        .help = h5_stage1: transitional test to NeXus, one file per frame, coord system wrong, do not use
        .help = h5: NeXus writer to H5 container, one file per rank
      h5 {
        dtype = *int32 uint16
          .type = choice
          .help = the numerical type, must be overall convertible to int32, uint16 is unsigned short
          .help = as in legacy nanoBragg::to_smv, the max limit for uint16 is 65534, not the usual 65535
        typecast = False
          .type = bool
          .help = Subtract 0.5 from the float-valued pixels, thus the Nexus writer behaves like SMV (cast to lower integer)
          .help = instead of nearest integer rounding.
      }
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
