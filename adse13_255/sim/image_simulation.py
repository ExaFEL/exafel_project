"""Simulate an image with Kokkos"""

from __future__ import absolute_import, division, print_function
from scipy import constants
from scitbx.array_family import flex
from scitbx.matrix import sqr
from simtbx.nanoBragg import nanoBragg, shapetype

from simtbx.nanoBragg.tst_gauss_argchk import water, basic_crystal, basic_detector, amplitudes

from dxtbx.model.beam import BeamFactory

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
  SIM.Ncells_abc = (20,20,20)
  SIM.Amatrix = sqr(CRYSTAL.get_A()).transpose()
  SIM.oversample = 2
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
  per_image_scale_factor = 1.0
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
      
if __name__=="__main__":
  from simtbx.kokkos import gpu_instance
  kokkos_run = gpu_instance(deviceId = 0)
  
  # make the dxtbx objects
  BEAM = basic_beam()
  DETECTOR = basic_detector()
  CRYSTAL = basic_crystal()
  
  SF_model = amplitudes(CRYSTAL)
  SF_model.random_structure(CRYSTAL)
  SF_model.ersatz_correct_to_P1()

  SIM = nanoBragg(DETECTOR, BEAM, panel_id=0)
  
  
  
  from LS49.spectra.generate_spectra import spectra_simulation
  spectra = spectra_simulation()
  spectra = spectra.generate_recast_renormalized_image(image=0%100000,energy=7120.,total_flux=1e12)
  wavlen, flux, wavelength_A = next(spectra) # list of lambdas, list of fluxes, average wavelength
  
  # print("\nassume three energy channels")
  # wavlen = flex.double([BEAM.get_wavelength()-0.002, BEAM.get_wavelength(), BEAM.get_wavelength()+0.002])
  # flux = flex.double([(1./6.)*SIM.flux, (3./6.)*SIM.flux, (2./6.)*SIM.flux])
  
  sfall_channels = {}
  for x in range(len(wavlen)):
    sfall_channels[x] = SF_model.get_amplitudes(at_angstrom = wavlen[x])
    
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
