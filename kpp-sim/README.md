This directory provides simulated images for demonstrating the ExaFEL KPPs.

Right now:

There is a [slurm script](./sim_5893005.sh) that gives a starting simulation of 100,000 images. 
Takes 30 minutes on 32 nodes of Perlmutter, writing files to scratch disk.
Adds Poisson noise and gain jitter (not present in NESAP benchmark).
Uses methane monooxygenase as the macromolecular crystal, for a spread simulation.
Writes images in individual files; later will use new code from Aaron to write NeXus.h5 containers


Usage for the weather plot [script](./weather.py): 
```
libtbx.python weather.py main_log_dir=/global/cfs/cdirs/lcls/sauter/LY99/cytochrome_sim rank_log_dir=$SCRATCH/cytochrome_sim jobid=5893005
#where
#  main_log_dir is the working area where you submit your jobs and write your slurm logs
#  rank_log_dir is the directory defined in the slurm script for holding the output data and rank logs
#  jobid is the SLURM jobid
```

Updated [slurm script sim_5946633.sh](./sim_5946633.sh) is work in progress trying to generalize the image simulation
to take arbitrary PDB coordinates and allow phil-defined parameter choices.

Updated [slurm script sim_6346286.sh](./sim_6346286.sh) is work in progress writing the image simulations to H5 containers,
one file per rank, instead of all-individual files.  Data are treated as int32, thus avoiding the Bragg spot overflows 
experienced with uint16 values in smv format.  Data are gzip-compressed in the H5.  There is one DETECTOR model overall
for the H5 file.  Each diffraction event has its own BEAM and SPECTRUM model.  Data are written in standard NeXus and therefore
suitable for DIALS input.  It needs to be confirmed that the data can be processed with dials.stills_process and cctbx.xfel.merge.
For the moment, the output.format=h5 option requires the nxmx_writer branches of both cctbx_project and dxtbx, however these 
will be merged in upcoming pull requests.
This is the most up to date version, with much more work to do.

compare_timings.py - show that reading in 100,000 patterns is faster from composite H5 than SMV.  This is the wall
time to read data from Perlmutter $SCR to RAM (non-persistent over loop) using 8 cpu nodes, 256 cpu ranks (32 ranks/cpu node).

| Format | Compression   | dtype           | Total size  | # files | Read time | Intake rate |
|--------|---------------|-----------------|-------------|---------|-----------|-------------|
| SMV    | external gzip | unsigned short  | 1.63 TB     | 100,000 | 197 s     | 0.066 Tb/s  |
| HDF5   | internal gzip | uint16 typecast | 1.77 TB     | 1024    | 167 s     | 0.085 Tb/s  |
| HDF5   | internal gzip | int32           | 1.73 TB     | 1024    | 181 s     | 0.076 Tb/s  |

compare_types.py - show that the uint16 HDF5 pixel values are identical to SMV.  However the metadata that determine 
the integration results are different.  Thus data processing for the two data formats will differ.

ferredoxin_index.sh and ferredoxin_merge.sh:  Slurm scripts for the H5 ferredoxin data processing. For SMV it
would be necessary to change dispatch.pre_import to False.

ferredoxin_index_8262276.sh and ferredoxin_merge_8275646.sh:  Better Slurm scripts for the H5 ferredoxin data processing, dispensing
entirely with dispatch.pre_import and (for now) implemented on the dials branch dsp_image_mode.

Updated [slurm script sim_6835899.sh](./sim_6835899.sh) writes out files in J16M detector format from SwissFEL.
Beam and Detector objects are read in from the provided *.expt file.

Updated [slurm script sim_ferredoxin_high_remote.sh](./sim_ferredoxin_high_remote.sh) simulates the same ferredoxin case except at the high-energy remote of 9500 eV.
Resolution limits are automatically calculated for the J16M detector.



