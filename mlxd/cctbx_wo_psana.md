# CONDA BUILD OF CCTBX WITHOUT PSANA for Power8/9

Assuming Conda ( Python-2.7 ) is already installed and available on path.
Conda packages must have support for `linux-ppc64le` architecture to work on PowerPC.
Potentially, we can build everything from scratch without conda if this does not work
using the original `base` installation of DIALS. Without CCI user accounts, we cannot
do an XFEL build, but the standard DIALS build will pull in all packages, less the 
closed-source ones requested by XFEL.

Begin by creating a new conda env. Often we need to specify at least 1 package to successfully 
create the env (system and version depending): 

```bash 
conda create -n cctbx_wo_psana -y anaconda-client
source activate cctbx_wo_psana
conda install h5py pillow numpy scipy libtiff
```

For packages not available in the Power conda repos, we can attempt to use `pip`. Before installing with `pip` 
make sure you have the MPI headers on your path; `module load openmpi` works on Cori. Command should be 
something similar on Summit. If any of the above packages fail to install, attempt to use p`pip` to pull them 
in, as it will attempt to build them from source:

```bash
pip install mpi4py 
```

Verify the conda python is default:
```bash
which python
```

Acquire the bootstrap script for cloning the CCTBX and required sources, then perform build:
```bash
curl -L https://raw.githubusercontent.com/cctbx/cctbx_project/master/libtbx/auto_build/bootstrap.py -o bootstrap.py
python bootstrap.py hot update --builder=dials #No need for closed source packages, so using DIALS is fine
python bootstrap.py build --builder=dials --with-python=$(which python) --nproc=<cores available>
```

The build may fail to recognise the architecture, (Linux on x86 vs Linux on PPC). We have no PPC test system here, so pass 
on the failure message logs and hopefully it can be a quick fix.

Next, run the tests with:
```bash
cctbx_regression.test_nightly
```
These steps may fail due to issues with dependencies, architecure specific settings, etc.
Another option is to run the base builder without conda, which builds an entire python distribution 
from scratch. This can take quite some time, but may succeed as everything is built from source. The steps outlined at 
http://dials.lbl.gov/documentation/installation_developer.html should be fine for this.
