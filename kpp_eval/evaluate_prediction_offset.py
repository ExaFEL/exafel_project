"""
Calculate, compare, and report the offset of observed vs predicted reflection
position in DIALS' stills_process vs diffBragg's hopper (stage 1).
"""
import glob
import sys
import os

import numpy as np
from pylab import *
from dials.array_family import flex
from joblib import Parallel, delayed

from exafel_project.kpp_eval.phil import parse_phil

# ggplot()
# xkcd()


phil_scope_str = """
stage1 = None
  .type = str
  .help = Directory with stage 1 results, the one containing folder refls
expt = None
  .type = str
  .help = Path to an expt files containing reference detector model. If None,
  .help = the first expt file found recursively in stage1/expers will be used.
d_min = 1.9
  .type = float
  .help = Lower bound of data resolution to be investigated, in Angstrom
d_max = 9999.
  .type = float
  .help = Upper bound of data resolution to be investigated
"""


NJ = 1
D_MIN = 9999.9
D_MAX = 2.0


def xy_to_polar(refl, DET, dials=False):
  x, y, _ = refl["xyzobs.px.value"]
  if dials:
    xcal, ycal, _ = refl["dials.xyzcal.px"]
  else:
    xcal, ycal, _ = refl["xyzcal.px"]

  pid = refl['panel']
  panel = DET[pid]
  x, y = panel.pixel_to_millimeter((x, y))
  xcal, ycal = panel.pixel_to_millimeter((xcal, ycal))

  xyz_lab = panel.get_lab_coord((x, y))
  xyz_cal_lab = panel.get_lab_coord((xcal, ycal))

  diff = np.array(xyz_lab) - np.array(xyz_cal_lab)

  xy_lab = np.array((xyz_lab[0], xyz_lab[1]))
  rad = xy_lab / np.linalg.norm(xy_lab)
  tang = np.array([-rad[1], rad[0]])

  rad_component = abs(np.dot(diff[:2], rad))
  tang_component = abs(np.dot(diff[:2], tang))
  pxsize = panel.get_pixel_size()[0]
  return rad_component / pxsize, tang_component / pxsize


def main(jid, njobs):
  from dxtbx.model import ExperimentList
  if len(sys.argv) == 2:
    curr_path = os.path.dirname(__file__)
    detpath = os.path.join(curr_path,
                           "../AD_SE_13_222/data_222/Jungfrau_model.json")
    DET = ExperimentList.from_file(detpath, False)[0].detector
  elif len(sys.argv) == 3:
    expt_name = sys.argv[2]
    DET = ExperimentList.from_file(expt_name, False)[0].detector

  fnames = glob.glob("%s/refls/rank*/*.refl" % sys.argv[1])
  print("%d fnames" % len(fnames))
  assert fnames
  all_d, all_d2 = [], []
  all_r, all_r2 = [], []
  all_t, all_t2 = [], []
  reso = []
  for i_f, f in enumerate(fnames):
    if i_f % njobs != jid:
      continue
    R = flex.reflection_table.from_file(f)
    if len(R) == 0:
      continue
    xyobs = R['xyzobs.px.value'].as_numpy_array()[:, :1]
    xycal = R['xyzcal.px'].as_numpy_array()[:, :1]
    reso += list(1. / np.linalg.norm(R['rlp'], axis=1))
    xycal2 = R['dials.xyzcal.px'].as_numpy_array()[:, :1]
    d = np.sqrt(np.sum((xyobs - xycal) ** 2, 1))
    d2 = np.sqrt(np.sum((xyobs - xycal2) ** 2, 1))
    all_d += list(d)
    all_d2 += list(d2)
    rad, theta = zip(
      *[xy_to_polar(R[i_r], DET, dials=False) for i_r in range(len(R))])
    rad2, theta2 = zip(
      *[xy_to_polar(R[i_r], DET, dials=True) for i_r in range(len(R))])
    all_r += list(rad)
    all_r2 += list(rad2)
    all_t += list(theta)
    all_t2 += list(theta2)
    # print(i_f)
  return all_d, all_d2, all_r, all_r2, all_t, all_t2, reso


results = Parallel(n_jobs=NJ)(delayed(main)(j, NJ) for j in range(NJ))

all_d, all_d2, all_r, all_r2, all_t, all_t2, reso = [], [], [], [], [], [], []  # zip(*results)
for d, d2, r, r2, t, t2, dspacing in results:
  all_d += d
  all_d2 += d2
  all_r += r
  all_r2 += r2
  all_t += t
  all_t2 += t2
  reso += dspacing

nbin = 10
# SAME-COUNT BINS
# bins = [b[0] - 1e-6 for b in np.array_split(np.sort(reso), nbin)] + [
#   max(reso) + 1e-6]

# SAME - VOLUME BINS
rec_cubed_start = pow(D_MIN if D_MIN else min(reso), -3)
rec_cubed_stop = pow(D_MAX if D_MAX else max(reso), -3)
rec_linspace = linspace(rec_cubed_start, rec_cubed_stop, nbin + 1)
bins = np.flip(np.power(rec_linspace, -1 / 3))

digs = np.digitize(reso, bins)

def np_rmsd(offset: np.ndarray) -> float:
  return np.sqrt(np.mean(offset ** 2))

all_d = np.array(all_d)
all_d2 = np.array(all_d2)
all_r = np.array(all_r)
all_r2 = np.array(all_r2)
all_t = np.array(all_t)
all_t2 = np.array(all_t2)
reso = np.array(reso)
ave_d, ave_d2, ave_r, ave_r2, ave_t, ave_t2, ave_res = [], [], [], [], [], [], []
for i_bin in range(1, nbin + 1):
  sel = digs == i_bin
  ave_d.append(np_rmsd(all_d[sel]))
  ave_d2.append(np_rmsd(all_d2[sel]))
  ave_r.append(np_rmsd(all_r[sel]))
  ave_r2.append(np_rmsd(all_r2[sel]))
  ave_t.append(np_rmsd(all_t[sel]))
  ave_t2.append(np_rmsd(all_t2[sel]))

  ave_res.append(np_rmsd(reso[sel]))

print("overall diffBragg pred offset: %.5f pixels" % np_rmsd(all_d))
print("overall DIALS pred offset: %.5f pixels" % np_rmsd(all_d2))

from tabulate import tabulate

print(tabulate(
  zip(*[ave_res, ave_d, ave_d2, ave_r, ave_r2, ave_t, ave_t2]),
  floatfmt=".3f",
  headers=("res (Ang)", "db (abs)", "DIALS (abs)", 'db (rad)', "DIALS (rad)",
           "db (tang)", "DIALS (tang)")))

for vals, vals2, title in [(ave_d, ave_d2, "overall"),
                           (ave_r, ave_r2, "radial component"),
                           (ave_t, ave_t2, "tangential component")]:
  figure()
  gca().set_title(title)
  plot(vals[::-1], color='chartreuse', marker='s', mec='k')
  plot(vals2[::-1], color="tomato", marker='o', mec='k')
  xticks = range(nbin)
  xlabels = ["%.2f" % r for r in ave_res]
  gca().set_xticks(xticks)
  gca().set_xticklabels(xlabels[::-1], rotation=90)
  gcf().set_size_inches((5, 4))
  subplots_adjust(bottom=0.2, left=0.15, right=0.98, top=0.9)
  gca().tick_params(labelsize=10, length=0)  # direction='in')
  grid(1, color="#777777", ls="--", lw=0.5)
  xlabel("resolution ($\AA$)", fontsize=11, labelpad=5)
  ylabel("prediction offset (pixels)", fontsize=11)
  leg = legend(("diffBragg", "DIALS"), prop={"size": 10})
  fr = leg.get_frame()
  fr.set_facecolor("bisque")
  fr.set_alpha(1)
  gca().set_facecolor("gainsboro")

show()


def run(parameters) -> None:
  pass


params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)
