"""
This script reports the value of map value, by default the anomalous signal
map, at the position of selected atoms, by default Fe and S.

This entire script is a refactor of `exafel_project/nks/map_height_at_atoms.py`
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

  UC = xray_structure.unit_cell()
  fgrid = [-1.,-.9,-.8,-.7,-.6,-.5,-.4,-.3,-.2,-.1,0.,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.]
  cutoff = {"Ca":7,"Mn":18}
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
    print( " site_vs_peak %4.2fÅ"%(sc_site_ortho - max_ortho).length(),
           " site_vs_centroid %4.2fÅ"%(sc_site_ortho - centroid).length(),
           " peak_vs_centroid %4.2fÅ"%(max_ortho - centroid).length(),
         )

if __name__ == '__main__':
  run(sys.argv[1:])
