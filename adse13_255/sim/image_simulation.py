"""Simulate an image with Kokkos"""

from __future__ import absolute_import, division, print_function
from scipy import constants
import numpy as np

import scitbx
import math
from scitbx.array_family import flex
from scitbx.matrix import sqr, col
from simtbx.nanoBragg import nanoBragg, shapetype

from simtbx.nanoBragg.tst_gauss_argchk import water, basic_detector, amplitudes

from dxtbx.model.beam import BeamFactory
from dxtbx.model.crystal import CrystalFactory

def modularized_exafel_api_for_KOKKOS(SIM,
                                      DETECTOR,
                                      BEAM, 
                                      CRYSTAL,
                                      flux,
                                      wavlen,
                                      sfall_channels,
                                      argchk=False, cuda_background=True):
  
  from simtbx.kokkos import gpu_energy_channels
  kokkos_channels_singleton = gpu_energy_channels()

  SIM.device_Id = 0

  assert kokkos_channels_singleton.get_nchannels() == 0 # uninitialized
  for x in range(len(flux)):
    kokkos_channels_singleton.structure_factors_to_GPU_direct(
    x, sfall_channels[x].indices(), sfall_channels[x].data())
  assert kokkos_channels_singleton.get_nchannels() == len(flux)
  N = CRYSTAL.number_of_cells(sfall_channels[0].unit_cell())
  SIM.Ncells_abc = (N,N,N)
  # SIM.Amatrix = sqr(CRYSTAL.get_A()).transpose()
  SIM.oversample = 1
  if argchk:
    print("\npolychromatic KOKKOS argchk")
    SIM.xtal_shape = shapetype.Gauss_argchk
  else:
    print("\npolychromatic KOKKOS no argchk")
    SIM.xtal_shape = shapetype.Gauss
  SIM.interpolate = 0
  # allocate GPU arrays
  from simtbx.kokkos import exascale_api
  kokkos_simulation = exascale_api(nanoBragg = SIM)
  kokkos_simulation.allocate()

  from simtbx.kokkos import gpu_detector as kokkosd
  kokkos_detector = kokkosd(detector=DETECTOR, beam=BEAM)
  kokkos_detector.each_image_allocate()

  # loop over energies
  for x in range(len(flux)):
      SIM.flux = flux[x]
      SIM.wavelength_A = wavlen[x]
      print("USE_EXASCALE_API+++++++++++++ Wavelength %d=%.6f, Flux %.6e, Fluence %.6e"%(
            x, SIM.wavelength_A, SIM.flux, SIM.fluence))
      kokkos_simulation.add_energy_channel_from_gpu_amplitudes(
        x, kokkos_channels_singleton, kokkos_detector)
  per_image_scale_factor = CRYSTAL.domains_per_crystal
  kokkos_detector.scale_in_place(per_image_scale_factor) # apply scale directly in KOKKOS
  
  SIM.wavelength_A = BEAM.get_wavelength() # return to canonical energy for subsequent background

  if cuda_background:
      SIM.Fbg_vs_stol = water
      SIM.amorphous_sample_thick_mm = 0.02
      SIM.amorphous_density_gcm3 = 1
      SIM.amorphous_molecular_weight_Da = 18
      SIM.flux=1e12
      SIM.beamsize_mm=0.003 # square (not user specified)
      SIM.exposure_s=1.0 # multiplies flux x exposure
      kokkos_simulation.add_background(kokkos_detector)

      # updates SIM.raw_pixels from GPU
      kokkos_detector.write_raw_pixels(SIM)
  else:
      # updates SIM.raw_pixels from GPU
      kokkos_detector.write_raw_pixels(SIM)

      SIM.Fbg_vs_stol = water
      SIM.amorphous_sample_thick_mm = 0.02
      SIM.amorphous_density_gcm3 = 1
      SIM.amorphous_molecular_weight_Da = 18
      SIM.flux=1e12
      SIM.beamsize_mm=0.003 # square (not user specified)
      SIM.exposure_s=1.0 # multiplies flux x exposure
      SIM.progress_meter=False
      SIM.add_background()
  return SIM


def basic_beam():
  print("Make a beam")
  # make a beam
  ENERGY = 9000
  ENERGY_CONV = 1e10*constants.c*constants.h / constants.electron_volt
  WAVELEN = ENERGY_CONV/ENERGY
  # dxtbx beam model description
  beam_descr = {'direction': (0.0, 0.0, 1.0),
             'divergence': 0.0,
             'flux': 1e11,
             'polarization_fraction': 1.,
             'polarization_normal': (0.0, 1.0, 0.0),
             'sigma_divergence': 0.0,
             'transmission': 1.0,
             'wavelength': WAVELEN}
  return BeamFactory.from_dict(beam_descr)

def basic_crystal():
  print("Make a randomly oriented xtal")
  # make a randomly oriented crystal..
  np.random.seed(3142019)
  # make random rotation about principle axes
  x = col((-1, 0, 0))
  y = col((0, -1, 0))
  z = col((0, 0, -1))
  rx, ry, rz = np.random.uniform(-180, 180, 3)
  RX = x.axis_and_angle_as_r3_rotation_matrix(rx, deg=True)
  RY = y.axis_and_angle_as_r3_rotation_matrix(ry, deg=True)
  RZ = z.axis_and_angle_as_r3_rotation_matrix(rz, deg=True)
  M = RX*RY*RZ
  real_a = M*col((79, 0, 0))
  real_b = M*col((0, 79, 0))
  real_c = M*col((0, 0, 38))
  # dxtbx crystal description
  cryst_descr = {'__id__': 'crystal',
               'real_space_a': real_a.elems,
               'real_space_b': real_b.elems,
               'real_space_c': real_c.elems,
               'space_group_hall_symbol': ' P 4nw 2abw'}
  return CrystalFactory.from_dict(cryst_descr)


# from LS49.adse13_196.revapi.LY99_pad import data


# Fe_oxidized_model = local_data.get("Fe_oxidized_model")
# Fe_reduced_model = local_data.get("Fe_reduced_model")
# Fe_metallic_model = local_data.get("Fe_metallic_model")


def data():
  from LS49.sim.fdp_plot import george_sherrell
  return dict(
    pdb_lines = open("1m2a.pdb","r").read(),
    Fe_oxidized_model = george_sherrell("pf-rd-ox_fftkk.out"),
    Fe_reduced_model = george_sherrell("pf-rd-red_fftkk.out"),
    Fe_metallic_model = george_sherrell("/Fe_fake.dat")
  )
  
if __name__=="__main__":
  from simtbx.kokkos import gpu_instance
  kokkos_run = gpu_instance(deviceId = 0)
  
  # make the dxtbx objects
  BEAM = basic_beam()
  DETECTOR = basic_detector()


  SIM = nanoBragg(DETECTOR, BEAM, panel_id=0)
  

  
  if 1:
    # energy spectrum
    from LS49.spectra.generate_spectra import spectra_simulation
    spectra = spectra_simulation()
    spectra = spectra.generate_recast_renormalized_image(image=0%100000,energy=7120.,total_flux=1e12)
    wavlen, flux, wavelength_A = next(spectra) # list of lambdas, list of fluxes, average wavelength
  else:
    print("\nassume three energy channels")
    wavlen = flex.double([BEAM.get_wavelength()-0.002, BEAM.get_wavelength(), BEAM.get_wavelength()+0.002])
    flux = flex.double([(1./6.)*SIM.flux, (3./6.)*SIM.flux, (2./6.)*SIM.flux])
  
  # breakpoint()
  wavelength_A = 1.74 # general ballpark X-ray wavelength in Angstroms
  wavlen = flex.double([12398.425/(7070.5 + w) for w in range(100)])
  direct_algo_res_limit = 1.7

  local_data = data()
  
  from LS49.sim.util_fmodel import gen_fmodel
  GF = gen_fmodel(resolution=direct_algo_res_limit,
                  pdb_text=local_data.get("pdb_lines"),algorithm="fft",wavelength=wavelength_A)
  GF.set_k_sol(0.435)
  GF.make_P1_primitive()

  # Generating sf for my wavelengths
  sfall_channels = {}
  for x in range(len(wavlen)):

    GF.reset_wavelength(wavlen[x])
    GF.reset_specific_at_wavelength(
                     label_has="FE1",tables=local_data.get("Fe_oxidized_model"),newvalue=wavlen[x])
    GF.reset_specific_at_wavelength(
                     label_has="FE2",tables=local_data.get("Fe_reduced_model"),newvalue=wavlen[x])
    sfall_channels[x]=GF.get_amplitudes()
    
  from LS49.adse13_196.revapi.LY99_pad import microcrystal
  CRYSTAL = microcrystal(Deff_A = 4000, length_um = 4., beam_diameter_um = 1.0) # assume smaller than 10 um crystals
  from LS49 import legacy_random_orientations
  random_orientation = legacy_random_orientations(1)
  rotation = sqr(random_orientation)

  SIM.mosaic_spread_deg = 0.05 # interpreted by UMAT_nm as a half-width stddev
                             # mosaic_domains setter MUST come after mosaic_spread_deg setter
  SIM.mosaic_domains = 25
  print ("MOSAIC",SIM.mosaic_domains)
  UMAT_nm = flex.mat3_double()
  mersenne_twister = flex.mersenne_twister(seed=0)
  scitbx.random.set_random_seed(1234)
  rand_norm = scitbx.random.normal_distribution(mean=0, sigma=SIM.mosaic_spread_deg * math.pi/180.)
  g = scitbx.random.variate(rand_norm)
  mosaic_rotation = g(SIM.mosaic_domains)
  for m in mosaic_rotation:
    site = col(mersenne_twister.random_double_point_on_sphere())
    UMAT_nm.append( site.axis_and_angle_as_r3_rotation_matrix(m,deg=False) )
  SIM.set_mosaic_blocks(UMAT_nm)
  SIM.Fhkl=sfall_channels[0] # instead of sfall_main
  Amatrix_rot = (rotation *
             sqr(sfall_channels[0].unit_cell().orthogonalization_matrix())).transpose()

  SIM.Amatrix_RUB = Amatrix_rot
  # fastest option, least realistic
  SIM.xtal_shape=shapetype.Gauss_argchk # both crystal & RLP are Gaussian  
  
  
  
  
  
  # sfall_channels = {}
  # for x in range(len(wavlen)):
  #   sfall_channels[x] = SF_model.get_amplitudes(at_angstrom = wavlen[x])
    
  print("\n# Use case: modularized api argchk=True, cuda_background=True")
  SIM6 = modularized_exafel_api_for_KOKKOS(SIM,
                                           DETECTOR,
                                           BEAM, 
                                           CRYSTAL,
                                           flux,
                                           wavlen,
                                           sfall_channels, argchk=True, cuda_background=True)
  SIM6.to_smv_format(fileout="test_full_e_006.img")
  SIM6.to_cbf("test_full_e_006.cbf")
