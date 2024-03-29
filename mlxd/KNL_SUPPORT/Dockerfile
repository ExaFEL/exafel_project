# Docker/Shifter container image of cctbx.xfel
# Designed for use with XTC data streams on NERSC's Cori
#
# Run bootstrap.py with hot and update first to get the modules directory.
# Next, add the Python2 Miniconda installer into the directory conttainer this file.
# Acquire the sources for MPICH3.2.1 and MPI4PY 3.0, untar them and place them here also.
# Run `docker build .` and wait for the image to build (may take some time)

FROM centos:centos7
MAINTAINER Lee O'Riordan <loriordan@lbl.gov>

RUN yum clean all &&  yum -y install bzip2.x86_64 libgomp.x86_64 telnet.x86_64 gcc-c++ gcc-gfortran && yum groupinstall "Development Tools" -y && yum -y install centos-release-scl-rh && yum -y install devtoolset-7-gcc devtoolset-7-gcc-c++ && scl enable devtoolset-7 bash

# https://repo.continuum.io/miniconda/
ADD Miniconda2-latest-Linux-x86_64.sh miniconda.sh
ADD bootstrap.py bootstrap.py
RUN chmod +x miniconda.sh && echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && /bin/bash miniconda.sh -b -p /opt/conda && rm miniconda.sh
ENV PATH $PATH:/opt/conda/bin
ENV LD_LIBRARY_PATH /lib64:$LD_LIBRARY_PATH:/opt/conda/lib

# psana-conda
RUN conda update -y conda && conda install -y --channel lcls-rhel7 psana-conda && conda install -y future h5py mpich2 wxpython pillow libtiff mock pytest jinja2 scikit-learn tabulate pytables scons mysql-python && conda install -y --channel conda-forge orderedset && /opt/conda/bin/python -m pip install procrunner && rm -rf /opt/conda/lib/python2.7/site-packages/numexpr-2.6.2-py2.7.egg-info

# recreate /reg/d directories for data
RUN mkdir -p /reg/g &&\
    mkdir -p /reg/d/psdm/CXI &&\
    mkdir -p /reg/d/psdm/cxi

# cctbx
ADD modules modules

RUN source  /opt/rh/devtoolset-7/enable; python bootstrap.py build --builder=xfel --with-python=/opt/conda/bin/python --nproc=4 2>&1 >> out.log; python bootstrap.py build --builder=xfel --with-python=/opt/conda/bin/python --nproc=4 2>&1 >> out.log; conda uninstall --force mpich2 2>&1 >> out.log; exit 0;

RUN mkdir -p /reg/d/psdm/mfx &&\
    mkdir -p /reg/d/psdm/MFX 

#Build Mpi4py from scratch against mpich
ADD mpich-3.2.1 /mpich_src
ADD mpi4py-3.0.0 /mpi4py_src

RUN scl enable devtoolset-7 bash && cd /mpich_src && ./configure && /usr/bin/make -j4 && /usr/bin/make install && /usr/bin/make clean && rm -rf /mpich_src && cd /mpi4py_src && /opt/conda/bin/python setup.py build && /opt/conda/bin/python setup.py install && rm -rf /mpi4py_src && /sbin/ldconfig

ENV PATH /opt/conda/bin:$PATH
ENV LD_LIBRARY_PATH /opt/conda/lib:$LD_LIBRARY_PATH
