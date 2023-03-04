"""
Extend the tests in tst_exafel_api to test KOKKOS vs CUDA
Both test cases excercise a simple monolithic detector
Test 1) standard C++ result CPU
     2) CPU, but use the stable sort version of CPU background (FUTURE PLAN)
     3) exafel api interface to GPU, fast evaluation on many energy channels, CPU background
     4) exafel api interface to GPU, fast evaluation on many energy channels, GPU background
     5) exafel api interface to KOKKOS, fast evaluation on many energy channels, KOKKOS background
     6) exafel api interface to KOKKOS, with GAUSS_ARGCHK
"""
from __future__ import absolute_import, division, print_function
from scitbx.array_family import flex
from scitbx.matrix import sqr
from simtbx.nanoBragg import nanoBragg, shapetype

from simtbx.nanoBragg.tst_gauss_argchk import water, basic_crystal, basic_beam, basic_detector, amplitudes

class several_wavelength_case:
 def __init__(self, BEAM, DETECTOR, CRYSTAL, SF_model):
  SIM = nanoBragg(DETECTOR, BEAM, panel_id=0)
  print("\nassume three energy channels")
  self.wavlen = flex.double([BEAM.get_wavelength()-0.002, BEAM.get_wavelength(), BEAM.get_wavelength()+0.002])
  self.flux = flex.double([(1./6.)*SIM.flux, (3./6.)*SIM.flux, (2./6.)*SIM.flux])
  self.sfall_channels = {}
  for x in range(len(self.wavlen)):
    self.sfall_channels[x] = SF_model.get_amplitudes(at_angstrom = self.wavlen[x])
  self.DETECTOR = DETECTOR
  self.BEAM = BEAM
  self.CRYSTAL = CRYSTAL

 def modularized_exafel_api_for_KOKKOS(self, argchk=False, cuda_background=True):
  from simtbx.kokkos import gpu_energy_channels
  kokkos_channels_singleton = gpu_energy_channels()

  SIM = nanoBragg(self.DETECTOR, self.BEAM, panel_id=0)
  SIM.device_Id = 0

  assert kokkos_channels_singleton.get_nchannels() == 0 # uninitialized
  for x in range(len(self.flux)):
          kokkos_channels_singleton.structure_factors_to_GPU_direct(
          x, self.sfall_channels[x].indices(), self.sfall_channels[x].data())
  assert kokkos_channels_singleton.get_nchannels() == len(self.flux)
  SIM.Ncells_abc = (20,20,20)
  SIM.Amatrix = sqr(self.CRYSTAL.get_A()).transpose()
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
  kokkos_detector = kokkosd(detector=self.DETECTOR, beam=self.BEAM)
  kokkos_detector.each_image_allocate()

  # loop over energies
  for x in range(len(self.flux)):
      SIM.flux = self.flux[x]
      SIM.wavelength_A = self.wavlen[x]
      print("USE_EXASCALE_API+++++++++++++ Wavelength %d=%.6f, Flux %.6e, Fluence %.6e"%(
            x, SIM.wavelength_A, SIM.flux, SIM.fluence))
      kokkos_simulation.add_energy_channel_from_gpu_amplitudes(
        x, kokkos_channels_singleton, kokkos_detector)
  per_image_scale_factor = 1.0
  kokkos_detector.scale_in_place(per_image_scale_factor) # apply scale directly in KOKKOS
  SIM.wavelength_A = self.BEAM.get_wavelength() # return to canonical energy for subsequent background

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


if __name__=="__main__":
  # make the dxtbx objects
  BEAM = basic_beam()
  DETECTOR = basic_detector()
  CRYSTAL = basic_crystal()
  SF_model = amplitudes(CRYSTAL)
  # Famp = SF_model.Famp # simple uniform amplitudes
  SF_model.random_structure(CRYSTAL)
  SF_model.ersatz_correct_to_P1()

  print("\n# Use case 2.  Three-wavelength polychromatic source")
  SWC = several_wavelength_case(BEAM, DETECTOR, CRYSTAL, SF_model)
  
  from simtbx.kokkos import gpu_instance
  kokkos_run = gpu_instance(deviceId = 0)

  print("\n# Use case: modularized api argchk=True, cuda_background=True")
  SIM6 = SWC.modularized_exafel_api_for_KOKKOS(argchk=True, cuda_background=True)
  SIM6.to_smv_format(fileout="test_full_e_006.img")
  SIM6.to_cbf("test_full_e_006.cbf")

print("OK")
