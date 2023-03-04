  from LS49.spectra.generate_spectra import spectra_simulation
  from LS49.sim.step4_pad import microcrystal
  
  

  wavelength_A = 1.74 # general ballpark X-ray wavelength in Angstroms
  wavlen = flex.double([12398.425/(7070.5 + w) for w in range(100)])
  direct_algo_res_limit = 1.7

  local_data = data() # later put this through broadcast

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
  
  
  spectra = spectra_simulation()
  CRYSTAL = microcrystal(Deff_A = 4000, length_um = 4., beam_diameter_um = 1.0) # assume smaller than 10 um crystals
  from LS49 import legacy_random_orientations
  random_orientation = legacy_random_orientations(1)
  rotation = sqr(random_orientation)
  spectra = spectra.generate_recast_renormalized_image(image=0%100000,energy=7120.,total_flux=1e12)
  
  wavlen, flux, wavelength_A = next(spectra) # list of lambdas, list of fluxes, average wavelength
  assert wavelength_A > 0