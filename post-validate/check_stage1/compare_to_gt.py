# coding: utf-8
"""
Usage: srun libtbx.python compare_to_gt.py ./path/to/stage1_outdir
"""
import pandas
from mpi4py import MPI
COMM = MPI.COMM_WORLD
import sys
import os
from copy import deepcopy
from dxtbx.model import ExperimentList

import h5py
from simtbx.diffBragg import utils

stage1_dir = sys.argv[1]
gt_ucell = 79.1, 79.1, 38.4, 90,90,90
symbol="P43212"

def print0(*args, **kwargs):
    if COMM.rank==0:
        print(*args, **kwargs)


import glob
cols = ["exp_name", "exp_idx", "ncells", "Amats", "a", "b", "c", "al", "be", "ga"]
pkls = glob.glob(os.path.join(stage1_dir, "pandas/hopper*rank*pkl"))
if not pkls:
    print("No input files found, check stage1 dir")
    exit()
dfs = []
for i_f, f in enumerate(pkls):
    if i_f % COMM.size != COMM.rank:
        continue
    print0("Loaded %d / %d pickles" %(i_f+1, len(pkls)), end="\r", flush=True)
    df = pandas.read_pickle(f)[cols]
    dfs.append(df)
df = pandas.concat(dfs).reset_index(drop=True)

angles = []
gt_ncells = None
refined_ucells = []
refined_ncells = []
for i_df, (e, i_exp, A, ncells) in enumerate(zip(df.exp_name, df.exp_idx, df.Amats, df.ncells)):
    expt = ExperimentList.from_file(e, False)[i_exp]
    C = expt.crystal
    C.set_A(tuple(A))

    refined_ucells.append( C.get_unit_cell().parameters() )

    h5 = expt.imageset.get_path(0)
    h5_idx = expt.imageset.indices()[0]
    gt_amat = h5py.File(h5, 'r')['model/rotation'][h5_idx]
    if gt_ncells is None:
        gt_ncells = h5py.File(h5, 'r')['model/Ncells_abc'][h5_idx]
    Cgt = deepcopy(C)
    Cgt.set_U(tuple(gt_amat.ravel()))
    a, b, c = Cgt.get_real_space_vectors()
    ang = utils.compare_with_ground_truth(a, b, c, [C], symbol=symbol)[0]
    angles.append(ang)
    ucell_s = ",".join(["%.3f" %u for u in refined_ucells[-1]])
    nabc_s = ",".join(["%.1f"%n for n in ncells])
    print("missori=%.5f deg.; ucell=[%s]; nabc=[%s] (shot %d / %d)" % (ang, ucell_s, nabc_s, i_df, len(df)))
    refined_ncells.append( ncells)

angles = COMM.reduce(angles)
refined_ncells = COMM.reduce(refined_ncells)
refined_ucells = COMM.reduce(refined_ucells)
if COMM.rank==0:
    import numpy as np
    med = np.median(angles)
    mn = np.mean(angles)
    sig = np.std(angles)
    print("\nRESULTS\n><><><><><><><><><><><>")
    print("Misori: Median, Mean, Stdev = %.4f , %.4f %.4f (degrees)" %(med, mn, sig))

    print("\nUnit cell stats:")
    labels = ["a", "b","c", "al", "be", "ga"]
    uc_meds = np.median(refined_ucells, axis=0)
    uc_mns= np.median(refined_ucells, axis=0)
    uc_sigs = np.std(refined_ucells, axis=0)
    units = ["Ang"]*3 + ["deg."]*3
    for name, med, mn, sig, unit in zip(labels, uc_meds, uc_mns, uc_sigs, units):
        print("%s: Median, Mean, Stdev = %.4f , %.4f %.4f (%s)" %(name, med, mn, sig, unit))

    print("\nNcells_abc stats:")
    labels = ["Na", "Nb", "Nc"]
    N_meds = np.median(refined_ncells, axis=0)
    N_mns= np.median(refined_ncells, axis=0)
    N_sigs = np.std(refined_ncells, axis=0)
    for name, med, mn, sig  in zip(labels, N_meds, N_mns, N_sigs):
        print("%s: Median, Mean, Stdev = %.4f , %.4f %.4f (unit cells)" %(name, med, mn, sig))
