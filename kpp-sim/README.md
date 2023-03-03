This directory provides simulated images for demonstrating the ExaFEL KPPs.

Right now:

There is a [slurm script](./sim_5893005.sh) that gives a starting simulation of 100,000 images. 
Takes 30 minutes on 32 nodes of Perlmutter, writing files to scratch disk.
Adds Poisson noise and gain jitter (not present in NESAP benchmark).
Uses methane monooxygenase as the macromolecular crystal, for a spread simulation.
Writes images in individual files; later will use new code from Aaron to write NeXus.h5 containers


Weather plot [script](./weather.py): 
