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
