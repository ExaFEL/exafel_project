import os

from dxtbx.model.experiment_list import ExperimentList
from LS49 import ls49_big_data
from LS49.sim.util_fmodel import gen_fmodel
from scitbx.array_family import flex

from scipy import constants

ENERGY_CONV = 1e10 * constants.c * constants.h / constants.electron_volt


def full_path(filename):
  return os.path.join(ls49_big_data, filename)


def data():
  from LS49.sim.fdp_plot import george_sherrell
  return dict(
    pdb_lines=open(full_path("7RF1_refine_030_Aa_refine_032_refine_034.pdb"), "r").read(),  # TODO? Or not?
    Mn_oxidized_model=george_sherrell(full_path("data_sherrell/Mn_spliced4+.dat")),  # TODO by Vidya
    Mn_reduced_model=george_sherrell(full_path("data_sherrell/Mn_spliced3+.dat")),  # TODO by Vidya
    Mn_metallic_model=george_sherrell(full_path("data_sherrell/Mn.dat"))
  )


def get_p20231_r0135_detector():
  expt_path = 't000_rg002_chunk000_reintegrated_000000.expt'
  return ExperimentList.from_file(expt_path)[0].detector


def psii_amplitudes_spread(comm):
  rank = comm.Get_rank()
  size = comm.Get_size()

  wavelength_A = 1.89  # general ballpark X-ray wavelength in Angstroms
  wavelengths = flex.double([ENERGY_CONV/(6520 + w) for w in range(81)])
  direct_algo_res_limit = 1.85

  local_data = data()  # later put this through broadcast

  # this is PDB 7RF1_refine_030_Aa_refine_032_refine_034
  GF = gen_fmodel(resolution=direct_algo_res_limit,
                  pdb_text=local_data.get("pdb_lines"),
                  algorithm="fft", wavelength=wavelength_A)
  GF.set_k_sol(0.435)
  GF.make_P1_primitive()

  # Generating sf for my wavelengths
  sfall_channels = {}
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

  reports = comm.gather(sfall_channels, root=0)
  if rank == 0:
    sfall_channels = {}
    for report in reports: sfall_channels.update(report)
  comm.barrier()
  return sfall_channels
