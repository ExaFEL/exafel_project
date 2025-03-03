"""
This script reports the value of map value, by default the anomalous signal
map, at the position of selected atoms, by default Mn and Ca.

This entire script is a refactor of `exafel_project/nks/map_height_at_atoms.py`

Usage:
libtbx.python exafel_project/kpp_eval/evaluate_anom_psii.py \
ls49_big_data/7RF1_refine_030_Aa_refine_032_refine_034.pdb \
/global/cfs/cdirs/m3562/users/dtchon/p20231/common/ensemble1/SPREAD2l/v000/SPREAD2l_v000_all.mtz \
selection="element Mn or element Ca" \
plot=False
"""

from __future__ import division, print_function

import sys

from libtbx.str_utils import make_sub_header
from libtbx.utils import Sorry
from scitbx.math import five_number_summary
from scitbx.array_family import flex
from scitbx.matrix import row

master_phil_str = """
map_type = anom
  .type = str
exclude_free_r_reflections = False
  .type = bool
fill_missing_f_obs = False
  .type = bool
resolution_factor = 0.25
  .type = float
selection = element FE or element S
  .type = atom_selection
plot = False
  .type = bool
"""

def master_phil():
  from mmtbx.command_line import generate_master_phil_with_inputs
  return generate_master_phil_with_inputs(
    phil_string=master_phil_str,
    enable_automatic_twin_detection=False)


def run(args, out=sys.stdout):
  usage_str = "python evaluate_anom.py model.pdb data.mtz [other phil pars]"
  import mmtbx.command_line
  cmdline = mmtbx.command_line.load_model_and_data(
    args=args,
    master_phil=master_phil(),
    process_pdb_file=False,
    prefer_anomalous=True,
    usage_string=usage_str,
    out=out)
  params = cmdline.params
  fmodel = cmdline.fmodel
  xray_structure = fmodel.xray_structure
  pdb_hierarchy = cmdline.pdb_hierarchy
  sel_cache = pdb_hierarchy.atom_selection_cache()
  selection = sel_cache.selection(params.selection).iselection()
  if not selection:
    raise Sorry("No atoms selected!")
  map_coeffs = fmodel.map_coefficients(
    map_type=params.map_type,
    exclude_free_r_reflections=params.exclude_free_r_reflections,
    fill_missing=params.fill_missing_f_obs)
  fft_map = map_coeffs.fft_map(
    resolution_factor=params.resolution_factor).apply_sigma_scaling()
  real_map = fft_map.real_map_unpadded()
  make_sub_header("Map analysis", out=out)

  grid5 = five_number_summary(real_map.as_1d())
  print(f'Grid points 5-number summary:', file=out)
  for n, v in zip('minimum quartile1 median quartile3 maximum'.split(), grid5):
    print(f'{n+":":21} {v:6.2f}σ', file=out)
  print('', file=out)
  return xray_structure, selection, real_map, params.plot, grid5

def geometry(xray_structure, selection, real_map, grid5):
  UC = xray_structure.unit_cell()
  fgrid = [-1.,-.9,-.8,-.7,-.6,-.5,-.4,-.3,-.2,-.1,0.,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.]
  cutoff = {"Ca":.3 * grid5[4],"Mn":0.7 * grid5[4]}
  result_store = {}
  for i_seq in selection:
    sc = xray_structure.scatterers()[i_seq]
    map_value = real_map.tricubic_interpolation(sc.site)
    print(f'{sc.label+":":21} {map_value:6.2f}σ',end="")
    sc_site_ortho = row(UC.orthogonalize(sc.site))
    all_ortho = flex.vec3_double()
    all_value = flex.double()
    # print statement for debug to prove ROI does not cover adjacent metal
    debug=False
    for dx in fgrid:
      if debug: print()
      for dy in fgrid:
        if debug: print()
        for dz in fgrid:
          d_site_ortho = (sc_site_ortho[0] + dx, sc_site_ortho[1] + dy, sc_site_ortho[2] + dz)
          d_site_frac = UC.fractionalize(d_site_ortho)
          d_value = real_map.tricubic_interpolation(d_site_frac)
          if d_value>cutoff[sc.element_symbol()]:
            all_ortho.append(d_site_ortho)
            all_value.append(d_value)
            if debug: print("%5.1f"%d_value, end="")
          else:
            pass
            if debug: print("     ", end="")
    if debug: print()
    max_ortho = row(all_ortho[flex.max_index(all_value)])
    weighted_ortho = all_ortho * all_value
    # no obvious good way to sum all the elements in a vec3_double, so do this:
    parts = weighted_ortho.parts()
    sum_weighted = flex.sum(parts[0]),flex.sum(parts[1]),flex.sum(parts[2])
    denom = flex.sum(all_value)
    centroid = row(( sum_weighted[0] / denom, sum_weighted[1] / denom, sum_weighted[2] / denom))
    result_store[sc.label]=dict(site=sc_site_ortho, peak=max_ortho, centroid=centroid)
    print( " site_vs_peak %4.2fÅ"%(sc_site_ortho - max_ortho).length(),
           " site_vs_centroid %4.2fÅ"%(sc_site_ortho - centroid).length(),
           " peak_vs_centroid %4.2fÅ"%(max_ortho - centroid).length(),
         )

  from tabulate import tabulate
  #sample output
  #print ("Mn 1 vs. 4 %4.2fÅ"%(result_store['pdb="MN1  OEX A 418 "']["centroid"] - result_store['pdb="MN4  OEX A 418 "']["centroid"]).length())
  data = []
  for atom_pair,L1,L2 in zip (["Mn 1 vs. 4","Mn 1 vs. 3","Mn 3 vs. 4"],[1,1,3],[4,3,4]):
    for monomer in ["A","a"]:
      label1 = 'pdb="MN%1d  OEX %1s 418 "'%(L1,monomer)
      label2 = 'pdb="MN%1d  OEX %1s 418 "'%(L2,monomer)
      drow = [atom_pair,monomer]
      for postype in "site","peak","centroid":
        position1 = result_store[label1][postype]
        position2 = result_store[label2][postype]
        drow.append("%4.2fÅ"%((position1 - position2).length()))
      data.append(drow)
  table = tabulate(
    data,
    headers=["Atom Pair", "Monomer", "Site distance", "Peak distance", "Centroid distance"],
    tablefmt="grid"
  )
  print(table)
  return result_store

def runplot(xray_structure, selection, real_map, result_store):
  from matplotlib import pyplot as plt
  import matplotlib.gridspec as gridspec
  UC = xray_structure.unit_cell()
  fgrid = [-0.2,-0.1,0.0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.,1.1,1.2]

  fig = plt.figure(figsize=(6,8))
  gs = gridspec.GridSpec(nrows=3, ncols=1, hspace=.5)
  igrid=-1
  for atom_pair,L1,L2 in zip (["Mn 1 vs. 4","Mn 1 vs. 3","Mn 3 vs. 4"],[1,1,3],[4,3,4]):
    igrid+=1
    ax = fig.add_subplot(gs[igrid,0])
    ax.set_title(atom_pair+" centroid section")
    for monomer in ["A","a"]:
      data = []
      label1 = 'pdb="MN%1d  OEX %1s 418 "'%(L1,monomer)
      label2 = 'pdb="MN%1d  OEX %1s 418 "'%(L2,monomer)
      postype = "centroid"
      position1 = result_store[label1][postype]
      position2 = result_store[label2][postype]
      diffvec = position2 - position1
      map_heights = []
      ortho = []
      for dx in fgrid:
        position_ortho = position1 + dx * diffvec
        d_site_frac = UC.fractionalize(position_ortho)
        d_value = real_map.tricubic_interpolation(d_site_frac)
        map_heights.append(d_value)
        ortho.append(dx * diffvec.length())
      ax.plot(ortho,map_heights,label="Monomer %s"%monomer)
    ax.set_xlabel("interatom position (Å)")
    ax.set_ylabel("Map height (σ)")
    ax.legend(loc="lower right")
  plt.show()


if __name__ == '__main__':
  xray_structure, selection, real_map, plot, grid5 = run(sys.argv[1:])
  #import pickle
  #with open("temp.pickle","wb") as F:
  #  pickle.dump((xray_structure, selection, real_map, plot, grid5), F)
  #with open("temp.pickle","rb") as F:
  #  xray_structure, selection, real_map, plot, grid5 = pickle.load(F)
  result_store = geometry(xray_structure, selection, real_map, grid5)
  if plot:
    runplot(xray_structure, selection, real_map, result_store)
