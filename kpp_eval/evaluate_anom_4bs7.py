"""
A version of the `evaluate_anom.py` designed specifically to inject
experimental f'' information to the model before calculating anomalous signal
"""

from __future__ import division, print_function

import os
import sys

from libtbx.str_utils import make_sub_header
from libtbx.utils import Sorry
from scitbx.math import five_number_summary


master_phil_str = """
map_type = anom
  .type = str
exclude_free_r_reflections = False
  .type = bool
fill_missing_f_obs = False
  .type = bool
resolution_factor = 0.25
  .type = float
selection = element Yb or element S
  .type = atom_selection
"""


def master_phil():
  from mmtbx.command_line import generate_master_phil_with_inputs
  return generate_master_phil_with_inputs(
    phil_string=master_phil_str,
    enable_automatic_twin_detection=False)


def enhance_fmodel_with_anomalous_dispersion(fmodel):
  """Replace fmodel.f_calc() with ones simulated assuming experimental
  Yb anomalous signal to reproduce structure factors used in diffBragg paper"""
  try:
    from cxid9114.sf.struct_fact_special import sfgen
    from cxid9114.parameters import WAVELEN_HIGH
  except ImportError as e:
    raise Sorry('Running this script requires cloning the cxid9114 repository '
                '(https://github.com/dermen/cxid9114/) to $MODULES') from e
  env_modules = os.environ.get('MODULES')
  pdb_path = os.path.join(env_modules, 'cxid9114/sim/4bs7.pdb')
  yb_path = os.path.join(env_modules, 'cxid9114/sf/scanned_fp_fdp.tsv')
  ma_original = fmodel.f_calc()
  ma_enhanced = sfgen(WAVELEN_HIGH, pdb_path, dmin=1.9, yb_scatter_name=yb_path)
  ma_new = ma_enhanced.common_set(ma_original)
  assert ma_new.size() == ma_original.size(), 'missing data in generated array'
  fmodel.update(f_calc=ma_new)
  return fmodel


def run(args, out=sys.stdout):
  usage_str = "python evaluate_anom.py model.pdb data.mtz [other phil pars]"
  import mmtbx.command_line
  with open(os.devnull, 'w') as devnull:
    cmdline = mmtbx.command_line.load_model_and_data(
      args=args,
      master_phil=master_phil(),
      process_pdb_file=False,
      prefer_anomalous=True,
      usage_string=usage_str,
      out=devnull)
  params = cmdline.params
  fmodel = cmdline.fmodel
  xray_structure = fmodel.xray_structure
  pdb_hierarchy = cmdline.pdb_hierarchy
  sel_cache = pdb_hierarchy.atom_selection_cache()
  selection = sel_cache.selection(params.selection).iselection()
  if not selection:
    raise Sorry("No atoms selected!")

  fmodel = enhance_fmodel_with_anomalous_dispersion(fmodel)
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

  for i_seq in selection:
    sc = xray_structure.scatterers()[i_seq]
    map_value = real_map.tricubic_interpolation(sc.site)
    print(f'{sc.label+":":21} {map_value:6.2f}σ', file=out)


if __name__ == '__main__':
  run(sys.argv[1:])
