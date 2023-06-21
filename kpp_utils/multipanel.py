from __future__ import division,print_function
from scitbx.array_family import flex
from scitbx.matrix import sqr,col
from simtbx.nanoBragg import shapetype
from simtbx.nanoBragg import nanoBragg
import libtbx.load_env # possibly implicit
from cctbx import crystal
import math
import scitbx
import os
from libtbx.development.timers import Profiler
from simtbx import get_exascale

def specific_expt(params):
  P = Profiler("Initialize specific expt file %s"%(params.detector.reference))
  from dxtbx.model.experiment_list import ExperimentList
  expt_path = params.detector.reference
  print("Opening the reference model experiment",params.detector.reference)
  expt_return = ExperimentList.from_file(expt_path, check_format=False)[0]
  mutate_root = expt_return.detector.hierarchy()
  x,y,z = mutate_root.get_origin()
  if z < 0: z -= params.detector.offset_mm
  else: z += params.detector.offset_mm
  mutate_root.set_frame(mutate_root.get_fast_axis(), mutate_root.get_slow_axis(), (x,y,z))
  return expt_return

def run_sim2h5(crystal,spectra,reference,rotation,rank,gpu_channels_singleton,params,
                quick=False,save_bragg=False,sfall_channels=None, **kwargs):
  DETECTOR = reference.detector
  PANEL = DETECTOR[0]

  wavlen, flux, shot_to_shot_wavelength_A = next(spectra) # list of lambdas, list of fluxes, average wavelength
  assert shot_to_shot_wavelength_A > 0 # wavelength varies shot-to-shot
  # os.system("nvidia-smi") # printout might severely impact performance

  # use crystal structure to initialize Fhkl array
  N = crystal.number_of_cells(sfall_channels[0].unit_cell())

  consistent_beam = reference.beam
  consistent_beam.set_wavelength(shot_to_shot_wavelength_A)
  SIM = nanoBragg(detector = DETECTOR, beam = consistent_beam)
  SIM.Ncells_abc=(N,N,N)
  print("beam, polar", SIM.beam_vector, SIM.polar_vector)

  SIM.adc_offset_adu = 0 # Do not offset by 40
  #SIM.adc_offset_adu = 10 # Do not offset by 40
  SIM.mosaic_spread_deg = 0.05 # interpreted by UMAT_nm as a half-width stddev
                               # mosaic_domains setter MUST come after mosaic_spread_deg setter
  SIM.mosaic_domains = int(os.environ.get("MOS_DOM","25"))
  print ("MOSAIC",SIM.mosaic_domains)
  SIM.distance_mm = PANEL.get_distance()
  print ("DISTANCE_mm",SIM.distance_mm)

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

  if params.attenuation:
    SIM.detector_thick_mm = 0.032 # = 0 for Rayonix
    SIM.detector_thicksteps = 1 # should default to 1 for Rayonix, but set to 5 for CSPAD
    SIM.detector_attenuation_length_mm = 0.017 # default is silicon

  # get same noise each time this test is run
  SIM.seed = 1
  SIM.oversample=1
  SIM.wavelength_A = shot_to_shot_wavelength_A
  SIM.polarization=1
  # this will become F000, marking the beam center
  SIM.default_F=0
  SIM.Fhkl=sfall_channels[0] # instead of sfall_main
  Amatrix_rot = (rotation *
             sqr(sfall_channels[0].unit_cell().orthogonalization_matrix())).transpose()

  SIM.Amatrix_RUB = Amatrix_rot
  #workaround for failing init_cell, use custom written Amatrix setter
  print("unit_cell_Adeg=",SIM.unit_cell_Adeg)
  print("unit_cell_tuple=",SIM.unit_cell_tuple)
  Amat = sqr(SIM.Amatrix).transpose() # recovered Amatrix from SIM
  from cctbx import crystal_orientation
  Ori = crystal_orientation.crystal_orientation(Amat, crystal_orientation.basis_type.reciprocal)

  # fastest option, least realistic
  SIM.xtal_shape=shapetype.Gauss_argchk # both crystal & RLP are Gaussian
  # only really useful for long runs
  SIM.progress_meter=False
  # prints out value of one pixel only.  will not render full image!
  # flux is always in photons/s
  SIM.flux=params.beam.total_flux
  SIM.exposure_s=1.0 # so total fluence is e12
  # assumes round beam
  SIM.beamsize_mm=0.003 #cannot make this 3 microns; spots are too intense
  temp=SIM.Ncells_abc
  SIM.Ncells_abc=temp

  # rough approximation to water: interpolation points for sin(theta/lambda) vs structure factor
  water_bg = flex.vec2_double([(0,2.57),(0.0365,2.58),(0.07,2.8),(0.12,5),(0.162,8),(0.18,7.32),(0.2,6.75),(0.216,6.75),(0.236,6.5),(0.28,4.5),(0.3,4.3),(0.345,4.36),(0.436,3.77),(0.5,3.17)])
  assert [a[0] for a in water_bg] == sorted([a[0] for a in water_bg])
  # rough approximation to air
  air_bg = flex.vec2_double([(0,14.1),(0.045,13.5),(0.174,8.35),(0.35,4.78),(0.5,4.22)])
  assert [a[0] for a in air_bg] == sorted([a[0] for a in air_bg])

  # simulated crystal is only 125 unit cells (25 nm wide)
  # amplify spot signal to simulate physical crystal of 4000x larger: 100 um (64e9 x the volume)
  SIM.raw_pixels *= crystal.domains_per_crystal; # must calculate the correct scale!

  QQ = Profiler("nanoBragg Bragg spots rank %d"%(rank))
  if True:
    #something new
    devices_per_node = int(os.environ["DEVICES_PER_NODE"])
    SIM.device_Id = rank%devices_per_node

    assert gpu_channels_singleton.get_deviceID()==SIM.device_Id
    if gpu_channels_singleton.get_nchannels() == 0: # if uninitialized
        P = Profiler("Initialize the channels singleton rank %d"%(rank))
        for x in range(len(flux) if params.absorption=="spread" else 1):
          gpu_channels_singleton.structure_factors_to_GPU_direct(
           x, sfall_channels[x].indices(), sfall_channels[x].data())
        del P
        import time
        print("datetime for channels singleton rank %d"%(rank),time.time())

    exascale_api = get_exascale("exascale_api", params.context)
    gpud = get_exascale("gpu_detector", params.context)

    gpu_simulation = exascale_api(nanoBragg = SIM)
    gpu_simulation.allocate()

    gpu_detector = gpud(deviceId=SIM.device_Id, detector=DETECTOR, beam=consistent_beam)
    gpu_detector.each_image_allocate()

    multipanel=(len(DETECTOR),DETECTOR[0].get_image_size()[0],DETECTOR[0].get_image_size()[1])
    image_grid = flex.grid(multipanel)
    positive_mask = ~(flex.bool(image_grid, False))
    positive_mask_iselection = positive_mask.iselection()

    # loop over energies
    for x in range(len(flux)):
      P = Profiler("USE_EXASCALE_API nanoBragg Python and C++ rank %d"%(rank))

      print("USE_EXASCALE_API+++++++++++++++++++++++ Wavelength",x)

      # from channel_pixels function
      SIM.wavelength_A = wavlen[x]
      SIM.flux = flux[x]
      channel_selection = 0 if params.absorption=="high_remote" else x
      gpu_simulation.add_energy_channel_mask_allpanel(
            channel_selection, gpu_channels_singleton, gpu_detector, positive_mask_iselection)
      del P
    gpu_detector.scale_in_place(crystal.domains_per_crystal) # apply scale directly on GPU
    SIM.wavelength_A = shot_to_shot_wavelength_A # return to canonical energy for subsequent background

    QQ = Profiler("nanoBragg background rank %d"%(rank))
    SIM.Fbg_vs_stol = water_bg
    SIM.amorphous_sample_thick_mm = 0.1
    SIM.amorphous_density_gcm3 = 1
    SIM.amorphous_molecular_weight_Da = 18
    SIM.flux=params.beam.total_flux
    SIM.beamsize_mm=0.003 # square (not user specified)
    SIM.exposure_s=1.0 # multiplies flux x exposure
    gpu_simulation.add_background(gpu_detector)
    SIM.Fbg_vs_stol = air_bg
    SIM.amorphous_sample_thick_mm = 10 # between beamstop and collimator
    SIM.amorphous_density_gcm3 = 1.2e-3
    SIM.amorphous_sample_molecular_weight_Da = 28 # nitrogen = N2
    gpu_simulation.add_background(gpu_detector)

    # gpu_detector.write_raw_pixels(SIM)  # updates SIM.raw_pixels from GPU ###################################################################NKS

    SIM.Amatrix_RUB = Amatrix_rot # return to canonical orientation
    del QQ

  if params.psf:
    SIM.detector_psf_kernel_radius_pixels=10;
    SIM.detector_psf_type=shapetype.Fiber # for Rayonix
    SIM.detector_psf_fwhm_mm=0.08
    #SIM.apply_psf() # the actual application is called within the C++ SIM.add_noise()
  else:
    #SIM.detector_psf_kernel_radius_pixels=5;
    SIM.detector_psf_type=shapetype.Unknown # for CSPAD
    SIM.detector_psf_fwhm_mm=0

  if params.noise:
    SIM.adc_offset_adu = 10 # Do not offset by 40
    SIM.detector_calibration_noise_pct = 1.0
    SIM.readout_noise_adu = 1.

  QQ = Profiler("nanoBragg noise rank %d"%(rank))
  if params.noise or params.psf:
    from LS49.sim.step6_pad import estimate_gain
    print("quantum_gain=",SIM.quantum_gain) #defaults to 1. converts photons to ADU
    print("adc_offset_adu=",SIM.adc_offset_adu)
    print("detector_calibration_noise_pct=",SIM.detector_calibration_noise_pct)
    print("flicker_noise_pct=",SIM.flicker_noise_pct)
    print("readout_noise_adu=",SIM.readout_noise_adu) # gaussian random number to add to every pixel (0 for PAD)
    # apply Poissonion correction, then scale to ADU, then adc_offset.
    # should be 10 for most Rayonix, Pilatus should be 0, CSPAD should be 0.
    print("detector_psf_type=",SIM.detector_psf_type)
    print("detector_psf_fwhm_mm=",SIM.detector_psf_fwhm_mm)
    print("detector_psf_kernel_radius_pixels=",SIM.detector_psf_kernel_radius_pixels)
    #estimate_gain(SIM.raw_pixels,offset=0)
    #SIM.add_noise() #converts photons to ADU.
    nominal_data = gpu_simulation.add_noise(gpu_detector)
    #estimate_gain(SIM.raw_pixels,offset=SIM.adc_offset_adu,algorithm="slow")
    #estimate_gain(SIM.raw_pixels,offset=SIM.adc_offset_adu,algorithm="kabsch")
  del QQ

  # nominal_data = gpu_detector.get_raw_pixels() # the normal way to gt the data, but shortcut due to noise call.
  gpu_detector.each_image_free() # deallocate GPU arrays

  if params.output.format == "h5":
    from dxtbx.model import Spectrum
    from cctbx import factor_ev_angstrom
    spectrum= Spectrum(factor_ev_angstrom/wavlen, flux)
    kwargs["writer"].add_beam_in_sequence(consistent_beam,spectrum)

    print ("ZINGA nominal", nominal_data, nominal_data.focus())
    # ad hoc code to recast as tuple of panel arrays
    npanel,nslow,nfast = nominal_data.focus()
    nominal_data.reshape(flex.grid((npanel*nslow,nfast)))
    reshape_data = tuple([ nominal_data[ip*nslow:(ip+1)*nslow, 0:nfast ] for ip in range(npanel)])
    kwargs["writer"].append_frame(data=reshape_data)

  SIM.free_all()
