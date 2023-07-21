from __future__ import division, print_function

import sys

from exafel_project.kpp_eval.phil import parse_input
from libtbx.str_utils import make_sub_header
from libtbx.utils import Sorry
from scitbx.math import five_number_summary


message = """
This script reports the value of map value, by default the anomalous signal
map, at the position of selected atoms, by default Fe and S. 

This entire script is a refactor of `exafel_project/nks/map_height_at_atoms.py`
""".strip()


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

  grid_fns = five_number_summary(real_map.as_1d())
  print(f'Grid points 5-number summary: {grid_fns!s}', file=out)
  for name, value in zip('min q_1 med q_3 max'.split(), grid_fns):
    print(f'{name}: {value:6.2f}', file=out)
  print('', file=out)

  for i_seq in selection:
    sc = xray_structure.scatterers()[i_seq]
    map_value = real_map.tricubic_interpolation(sc.site)
    print(f'{sc.label:8}: {map_value:6.2f}σ', file=out)


params = []
if __name__ == '__main__':
  params, options = parse_input()
  if '-h' in options or '--help' in options:
    print(message)
    exit()
  run(params)
