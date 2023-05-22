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
    absorption = *spread high_remote
      .type = choice
      .help = either do a spread calculation, which calculates wavelength-dependent amplitudes, or
      .help = a high_remote energy calculation, where amplitudes are only calculated at the mean energy
    res_limit = None
      .type = float
    beam {
      mean_energy = None
        .type = float
        .optional = False
        .help = spectra from big data are coerced to this mean energy given in units of eV
      total_flux = 1E12
        .type = float
        .help = spectra from big data are coerced to this total flux
    }
    spectrum {
      nchannels = 100
        .type = int
        .help = number of energy channels for spectrum simulation
      channel_width = 1.0
        .type = float
        .help = width of one energy channel in eV.
    }
    crystal {
      structure = *ferredoxin PSII pdb
        .type = choice
        .help = type of crystal structure to be simulated
      pdb {
        source = *code file
          .type = choice
          .help = Download the code directly from PDB or source it from a local file?
          .help = Not implemented yet.  Always assume PDB download.
        code = None
          .type = str
          .help = PDB code of the structure to be simulated
        file = None
          .type = path
          .help = local path for the file, either pdb atom coordinates or structure factors
        coefficients = fobs *fcalc
          .type = choice
          .help = get the Fourier coefficients from either Fmodel (fcalc) or experimental file (fobs)
        label = None
          .type = str
          .help = if coefficients=fobs, identify the column label to use from the *-sf.cif?
          .help = Label value should be a short substring for matching, like "tensity" in "pdbx_intensity"
          .help = To identify the available labels use exafel_project/kpp_utils/labels.py <filename or pdb_code>
      }
      length_um = 4.0
        .type = float
        .help = beam path length through the crystal in microns
    }
    detector {
      tiles = *single multipanel
        .type = choice
        .help = use fundamentally different function calls for single panel or multipanel detectors
      reference = None
        .type = path
        .help = give the *.expt file to serve as reference for both beam and detector
      offset_mm = 0.0
        .type = float
        .help = detector distance offset applied to the input reference model.  Note that this is a signed
        .help = quantity defined in common sense terms.  A positive quantity moves the detector further
        .help = from the crystal, even if the z-coordinate of the detector is negative, and a negative
        .help = quantity moves closer to the crystal.  This is an offset from the reference, not an absolute.
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
