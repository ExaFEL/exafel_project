from __future__ import division
import os

from LS49 import ls49_big_data
from LS49.sim.util_fmodel import gen_fmodel
from scitbx.array_family import flex

from exafel_project.kpp_utils.mp_utils import collect_large_dict

from scipy import constants
ENERGY_CONV = 1e10 * constants.c * constants.h / constants.electron_volt


def full_path(filename):
  return os.path.join(ls49_big_data, filename)


def data():
  from LS49.sim.fdp_plot import george_sherrell
  return dict(
    pdb_lines=open(full_path("7RF1_refine_030_Aa_refine_032_refine_034.pdb"), "r").read(),
    Mn_oxidized_model=george_sherrell(full_path("data_sherrell/MnO2_spliced.dat")),
    Mn_reduced_model=george_sherrell(full_path("data_sherrell/Mn2O3_spliced.dat")),
    Mn_metallic_model=george_sherrell(full_path("data_sherrell/Mn.dat"))
  )

def amplitudes_spread_psii(comm, params, **kwargs):
  rank = comm.Get_rank()
  size = comm.Get_size()

  wavelength_A = ENERGY_CONV / params.beam.mean_energy
  # general ballpark X-ray wavelength in Angstroms, does not vary shot-to-shot
  centerline = float(params.spectrum.nchannels-1)/2.0
  channel_mean_eV = (flex.double(range(params.spectrum.nchannels)) - centerline
                      ) * params.spectrum.channel_width + params.beam.mean_energy
  wavelengths = ENERGY_CONV/channel_mean_eV
  direct_algo_res_limit = kwargs.get("direct_algo_res_limit", 1.85)

  local_data = data()  # later put this through broadcast

  # this is PDB 7RF1_refine_030_Aa_refine_032_refine_034
  GF = gen_fmodel(resolution=direct_algo_res_limit,
                  pdb_text=local_data.get("pdb_lines"),
                  algorithm="fft", wavelength=wavelength_A)
  GF.set_k_sol(0.435)
  GF.make_P1_primitive()

  # Generating sf for my wavelengths
  sfall_channels = {}

  if params.absorption == "high_remote":
    if rank==0:
      sfall_channels[0] = GF.get_amplitudes()
    return sfall_channels

  for x in range(len(wavelengths)):
    if rank > len(wavelengths): break
    if x % size != rank: continue

    GF.reset_wavelength(wavelengths[x])  # TODO: which to make 3+ and which 4+?
    GF.reset_specific_at_wavelength(label_has="MN1",
                                    tables=local_data.get("Mn_oxidized_model"),
                                    newvalue=wavelengths[x])
    GF.reset_specific_at_wavelength(label_has="MN2",
                                    tables=local_data.get("Mn_oxidized_model"),
                                    newvalue=wavelengths[x])
    GF.reset_specific_at_wavelength(label_has="MN3",
                                    tables=local_data.get("Mn_reduced_model"),
                                    newvalue=wavelengths[x])
    GF.reset_specific_at_wavelength(label_has="MN4",
                                    tables=local_data.get("Mn_reduced_model"),
                                    newvalue=wavelengths[x])
    sfall_channels[x] = GF.get_amplitudes()

  sfall_channels = collect_large_dict(comm, sfall_channels, root=0)
  comm.barrier()
  return sfall_channels

def amplitudes_pdb(comm, params, **kwargs):
  """ Matrix of choices for data source
                                               params.crystal.pdb.source
                                                code               file
    params.crystal.pdb.coefficients        |---------------|---------------|
                   fcalc                   |               |               |
                                           |---------------|---------------|
                   fobs                    |               |               |
                                           |---------------|---------------|
  """
  rank = comm.Get_rank()
  if params.absorption != "high_remote":
    raise ValueError("crystal.structure=pdb is only implemented for absorption=high_remote")
  assert len(params.crystal.pdb.code)==4 # for the moment codes are always 4 characters
  # Generating sf for my wavelengths
  sfall_channels = {}
  direct_algo_res_limit = kwargs.get("direct_algo_res_limit", 1.85)

  if params.crystal.pdb.coefficients=="fcalc":
    if rank==0:
      from iotbx.pdb.fetch import fetch
      pdb_lines = fetch(params.crystal.pdb.code).read().decode() # bytes to str

      wavelength_A = ENERGY_CONV / params.beam.mean_energy
      # general ballpark X-ray wavelength in Angstroms, does not vary shot-to-shot
      centerline = float(params.spectrum.nchannels-1)/2.0
      channel_mean_eV = (flex.double(range(params.spectrum.nchannels)) - centerline
                      ) * params.spectrum.channel_width + params.beam.mean_energy
      wavelengths = ENERGY_CONV/channel_mean_eV

      GF = gen_fmodel(resolution=direct_algo_res_limit,
                  pdb_text=pdb_lines,
                  algorithm="fft", wavelength=wavelength_A)
      GF.set_k_sol(0.435)

      if params.output.ground_truth is not None:
        # write the fcalc to file so it can be later used as control for hopper
        hi_sym_amplitudes = GF.get_amplitudes()
        mtz_out = hi_sym_amplitudes.as_mtz_dataset(
          column_root_label="F",
          title="ground truth reference amplitudes",
          wavelength=wavelength_A)
        mtz_obj = mtz_out.mtz_object()
        mtz_obj.write(params.output.ground_truth) # mtz file name

      GF.make_P1_primitive()
      sfall_channels[0] = GF.get_amplitudes()

  else:
    assert params.crystal.pdb.coefficients=="fobs"
    if rank==0:
      from iotbx import reflection_file_reader
      if params.crystal.pdb.source=="file":
        miller_arrays = reflection_file_reader.any_reflection_file(file_name =
          params.crystal.pdb.file).as_miller_arrays()

      else: # lookup by PDB code
        from iotbx.pdb.fetch import fetch
        lines = fetch(id=params.crystal.pdb.code,data_type="xray",format="cif")
        miller_arrays = reflection_file_reader.cif_reader(file_object = lines).as_miller_arrays()

      for ma in miller_arrays:
        print(ma.info().label_string())
        if params.crystal.pdb.label.lower() in ma.info().label_string().lower():
          break
      assert params.crystal.pdb.label.lower() in ma.info().label_string().lower()
      mae = ma.expand_to_p1()
      # assert mae.is_xray_intensity_array() # doesn't always have to be intensities
      maec = mae.complete_array(d_min=direct_algo_res_limit)

      sfall_channels[0] = maec.as_amplitude_array() # amplitudes in anomalous P1 cell out to direct_algo_res_limit

  return sfall_channels
