# coding: utf-8
"""
Usage: srun libtbx.python compare_to_gt.py ./path/to/stage1_outdir --figname hist.png --nbins 50
"""
import pandas
import numpy as np
from mpi4py import MPI
COMM = MPI.COMM_WORLD
import sys
import os
from copy import deepcopy
from dxtbx.model import ExperimentList

import h5py
from simtbx.diffBragg import utils

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("dirname", type=str, help="stage 1 output folder")
parser.add_argument("--symbol", type=str, default=None, help="space group lookup symbol (e.g. P212121). If not provided, will be read from DIALS crystal models")
parser.add_argument("--figname", type=str, default=None, help="If provided, will save a histogram plot to this file.")
parser.add_argument("--nbins", default=70, type=int, help="Number of histogram bins")
parser.add_argument("--logbins", action="store_true", help="whether to use log-spaced bins for the histogram")
args = parser.parse_args()

stage1_dir = args.dirname

def print0(*args, **kwargs):
    if COMM.rank==0:
        print(*args, **kwargs)


import glob
cols = ["exp_name", "exp_idx", "ncells", "Amats", "a", "b", "c", "al", "be", "ga", "eta_abc", "eta", "sigz", "niter"]
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

angles = []
angles_dials = []
refined_ucells = []
refined_ncells = []
refined_etas = []
sigzs = []
tdata = []

if dfs:
    df = pandas.concat(dfs).reset_index(drop=True)
    gt_ncells = None
    for i_df, (e, i_exp, A, ncells, etas, sigz) in enumerate(zip(df.exp_name, df.exp_idx, df.Amats, df.ncells, df.eta_abc, df.sigz)):
        expt = ExperimentList.from_file(e, False)[i_exp]
        C = expt.crystal
        C_dials = deepcopy(C)
        C.set_A(tuple(A))

        refined_ucells.append(C.get_unit_cell().parameters() )

        h5 = expt.imageset.get_path(0)
        h5_idx = expt.imageset.indices()[0]
        gt_amat = h5py.File(h5, 'r')['model/Umatrix_rot'][h5_idx]
        if gt_ncells is None:
            gt_ncells = h5py.File(h5, 'r')['model/Ncells_abc'][h5_idx]
        Cgt = deepcopy(C)
        Cgt.set_U(tuple(gt_amat.ravel()))
        a, b, c = Cgt.get_real_space_vectors()
        symbol = args.symbol
        if args.symbol is None:
            symbol = C.get_space_group().info().type().lookup_symbol()
            print(symbol)
        ang = utils.compare_with_ground_truth(a, b, c, [C], symbol=symbol)[0]
        ang_dials = utils.compare_with_ground_truth(a, b, c, [C_dials], symbol=symbol)[0]
        angles.append(ang)
        angles_dials.append(ang_dials)
        ucell_s = ",".join(["%.3f" %u for u in refined_ucells[-1]])
        nabc_s = ",".join(["%.1f"%n for n in ncells])
        print("missori=%.5f -> %.5f deg.; ucell=[%s]; nabc=[%s] (shot %d / %d)" % (ang_dials, ang, ucell_s, nabc_s, i_df, len(df)))
        tdata.append(" ".join(["%.6f"%u for u in refined_ucells[-1]]) + " %s"%("".join(symbol.split())))
        refined_ncells.append( ncells)
        refined_etas.append(etas)
        sigzs.append(sigz)

angles = COMM.reduce(angles)
angles_dials = COMM.reduce(angles_dials)
refined_ncells = COMM.reduce(refined_ncells)
refined_etas = COMM.reduce(refined_etas)
refined_ucells = COMM.reduce(refined_ucells)
sigzs = COMM.reduce(sigzs)
tdata = COMM.reduce(tdata)
if COMM.rank==0:
    #handle tdata
    tdata_file = os.path.join(os.getcwd(),"tdata_cells.tdata")
    mycluster = "uc_metrics.dbscan file_name=%s space_group=Pmmm eps=0.02 feature_vector=a,b,c write_covariance=False plot.outliers=False"%tdata_file
    with open(tdata_file,"w") as F:
      F.write("\n".join(tdata))
      print("Plot unit cell distribution with\n%s"%mycluster)

    # PRINT RESULTS
    med_d = np.median(angles_dials)
    mn_d = np.mean(angles_dials)
    sig_d = np.std(angles_dials)
    med = np.median(angles)
    mn = np.mean(angles)
    sig = np.std(angles)
    print("\nRESULTS\n><><><><><><><><><><><>")
    print("Init misori: Median, Mean, Stdev = %.4f , %.4f %.4f (degrees)" %(med_d, mn_d, sig_d))
    print("Final misori: Median, Mean, Stdev = %.4f , %.4f %.4f (degrees)" %(med, mn, sig))

    from scipy.stats import rayleigh
    assert(np.min(angles_dials) >= 0.)
    param_angles_dials = rayleigh.fit(angles_dials, floc=0.) # distribution fitting
    assert(np.min(angles) >= 0.)
    param_angles_stge1 = rayleigh.fit(angles, floc=0., method="MM")
    print("Init misori: Rayleigh scale, Max = %.4f , %.4f (degrees)" %
                          (param_angles_dials[1],np.max(angles_dials)))
    print("Final misori:Rayleigh scale, Max = %.4f , %.4f (degrees)" %
                          (param_angles_stge1[1],np.max(angles)))
    print("\nUnit cell stats:")
    labels = ["a", "b","c", "al", "be", "ga"]
    uc_mins = np.min(refined_ucells, axis=0)
    uc_maxs = np.max(refined_ucells, axis=0)
    uc_meds = np.median(refined_ucells, axis=0)
    uc_mns= np.median(refined_ucells, axis=0)
    uc_sigs = np.std(refined_ucells, axis=0)
    units = ["Ang"]*3 + ["deg."]*3
    for name, minu, maxu, med, mn, sig, unit in zip(labels, uc_mins, uc_maxs, uc_meds, uc_mns, uc_sigs, units):
        print("%2s: Min-Max, Median, Mean, Stdev = %8.4f-%8.4f, %8.4f , %8.4f %8.4f (%s)" %(name, minu, maxu, med, mn, sig, unit))

    print("\nNcells_abc stats:")
    labels = ["Na", "Nb", "Nc"]
    N_meds = np.median(refined_ncells, axis=0)
    N_mns= np.median(refined_ncells, axis=0)
    N_sigs = np.std(refined_ncells, axis=0)
    for name, med, mn, sig  in zip(labels, N_meds, N_mns, N_sigs):
        print("%s: Median, Mean, Stdev = %.4f , %.4f %.4f (unit cells)" %(name, med, mn, sig))
    print("Ground truth Ncells_abc=", gt_ncells)


    print("\n<Eta_abc>:")
    labels = ["eta_a", "eta_b", "eta_c"]
    eta_meds = np.median(refined_etas, axis=0)
    eta_mns= np.median(refined_etas, axis=0)
    eta_sigs = np.std(refined_etas, axis=0)
    for name, med, mn, sig  in zip(labels, eta_meds, eta_mns, eta_sigs):
        print("%s: Median, Mean, Stdev = %.4f , %.4f %.4f (unit cells)" %(name, med, mn, sig))
    print("Ground truth Eta_abc=0.05 (is this right?)")

    print("\n<SigmaZ>")
    N_meds = np.median(refined_ncells, axis=0)
    N_mns= np.median(refined_ncells, axis=0)
    N_sigs = np.std(refined_ncells, axis=0)
    print("Min - Max, Median Mean = %.4f - %.4f, %.4f %.4f" %(
        np.min(sigzs), np.max(sigzs), np.median(sigzs), np.mean(sigzs)))

    # MAKEPLOT
    import pylab as plt
    fig, ax = plt.subplots(1,1)
    fig.set_size_inches((5.5,3))
    all_ang = np.hstack((angles, angles_dials))
    if args.logbins:
        bins = np.logspace(np.log10(all_ang.min()), np.log10(all_ang.max()), args.nbins)
    else:
        bins = np.linspace(0, np.max(all_ang), args.nbins)

    med = np.median(angles)
    med_dials = np.median(angles_dials)
    hist_args = {"histtype":"step", "lw":1.5,"alpha":0.8}
    heights=plt.hist(angles,bins=bins,
            label="diffBragg, median=%.4f$\degree$" % med,
            **hist_args)[0]
    heights_dials=plt.hist(angles_dials, bins=bins ,
            label="DIALS, median=%.4f$\degree$" % med_dials,
            color='tomato', **hist_args)[0]

    rayleigh_fit_dials = rayleigh.pdf(bins,loc=param_angles_dials[0],scale=param_angles_dials[1])
    plt.plot(bins,rayleigh_fit_dials,'r-')
    rayleigh_fit_stge1 = rayleigh.pdf(bins,loc=param_angles_stge1[0],scale=param_angles_stge1[1])
    plt.plot(bins,rayleigh_fit_stge1,'b-')

    ax.set_xlabel("Crystal misorientation (°)")
    if args.logbins:
        ax.set_xscale("log")
    ax.set_ylabel("# of images")
    ax.grid(1, which='both', ls='--')
    plt.legend()
    plt.subplots_adjust(left=.1, bottom=.18, right=.96, top=.94)
    if args.figname is not None:
        plt.savefig(args.figname, dpi=500)

    fig, ax = plt.subplots(1,1)
    ax.set_xlabel("<$\sigma$Z>")
    ax.set_ylabel("# of images")
    heights_sigz=plt.hist(sigzs, bins=args.nbins ,
            label="$\sigma$Z, median=%.4f" % np.median(sigzs),
            color='tomato')[0]
    plt.legend()
    plt.show()

