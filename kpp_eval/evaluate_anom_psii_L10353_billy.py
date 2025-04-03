"""
Usage:
libtbx.python evaluate_anom_psii_L10353_billy.py \
$MODULES/ls49_big_data/7RF1_refine_030_Aa_refine_032_refine_034.pdb \
/global/cfs/cdirs/m3562/users/dtchon/p20231/common/ensemble1/SPREAD2l/v000/SPREAD2l_v000_all.mtz \
selection="element Mn" \
miller_array.labels.name="Iobs" \
xray_data.high_resolution=3.0
"""
from __future__ import division, print_function
import sys
from libtbx.str_utils import make_sub_header
from libtbx.utils import Sorry
from scitbx.math import five_number_summary
from scitbx.array_family import flex
from scitbx.matrix import row
from iotbx.cli_parser import run_program
from libtbx.program_template import ProgramTemplate

"""Issues to resolve with Billy
1) prefer_anomalous=True
8) enable automatic twin detection
"""

# =============================================================================
class MyProgram(ProgramTemplate):

  description = 'This is a test program'

  # expected file types when processed by the DataManager
  datatypes = ['miller_array', 'model', 'phil']

  # your PHIL parameters
  # this is for setting the scattering table to use
  master_phil_str = '''
my_parameter = wk1995 it1992 *n_gaussian electron neutron
  .type = choice(multi=False)
  .short_caption = Scattering table
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
  .help = False writes plot to png file, True to x-terminal
'''
  # program-specific custom settings for established phil parameters
  data_manager_custom_master_phil_str = '''
data_manager.fmodel.xray_data.r_free_flags.required=False
'''

  # this shows the standard DataManager PHIL scope containing fmodel parameters
  show_data_manager_scope_by_default = True

  # this makes changing the scattering table consistent with the data types in the DataManager
  use_scattering_table_for_default_type = 'my_parameter'

  # ---------------------------------------------------------------------------
  def validate(self):
    '''
    Basic checks to see if it is possible to run the program

    After parsing the command-line arguments, PHIL parameters are in self.params
    and files are loaded into the self.data_manager

    Sorry is raised with standard error messages if a check fails.
    '''
    self.data_manager.has_models(expected_n=1, exact_count=True, raise_sorry=True)
    self.data_manager.has_miller_arrays(expected_n=1, exact_count=True, raise_sorry=True)

  # ---------------------------------------------------------------------------
  def run(self):
    '''
    Main processing code should be in this function.

    With one model and one reflection file, the DataManager can figure out which
    arrays should be used. If the reflection file has multiple arrays, the selection
    can be done at the command line.
    '''
    self.fmodel = self.data_manager.get_fmodel(scattering_table=self.params.my_parameter)
    make_sub_header("X-ray scattering dictionary", out=sys.stdout)
    self.fmodel.xray_structure.scattering_type_registry().show(out = self.logger)
    make_sub_header("F(model) initialization", out=sys.stdout)
    self.fmodel.update_all_scales(log=self.logger)
    self.fmodel.show()

    model_obj = self.data_manager.get_model()
    sel_cache = model_obj.get_atom_selection_cache()
    selection = sel_cache.selection(self.params.selection).iselection()
    if not selection:
      raise Sorry("No atoms selected!")
    map_coeffs = self.fmodel.map_coefficients(
      map_type=self.params.map_type,
      exclude_free_r_reflections=self.params.exclude_free_r_reflections,
      fill_missing=self.params.fill_missing_f_obs)
    fft_map = map_coeffs.fft_map(
      resolution_factor=self.params.resolution_factor).apply_sigma_scaling()
    self.real_map = fft_map.real_map_unpadded()
    make_sub_header("Map analysis", out=sys.stdout)

    self.grid5 = five_number_summary(self.real_map.as_1d())
    print(f'Grid points 5-number summary:', file=sys.stdout)
    for n, v in zip('minimum quartile1 median quartile3 maximum'.split(), self.grid5):
      print(f'{n+":":21} {v:6.2f}σ', file=sys.stdout)
    print('', file=sys.stdout)
    self.selection = selection

  # ---------------------------------------------------------------------------
  def get_results(self):
    '''
    The thing to be returned
    '''
    return self.fmodel.xray_structure, self.selection, self.real_map, self.params.plot, self.grid5

# =============================================================================

def geometry(xray_structure, selection, real_map, grid5):
  make_sub_header("Anomalous peaks")
  UC = xray_structure.unit_cell()
  fgrid = [-1.,-.9,-.8,-.7,-.6,-.5,-.4,-.3,-.2,-.1,0.,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.]
  cutoff = {"Ca":.25 * grid5[4],"Mn":0.6 * grid5[4]}
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
    result_store[sc.label]=dict(site=sc_site_ortho, peak=max_ortho, centroid=centroid, map_value=map_value, element=sc.element_symbol())
    print( " site_vs_peak %4.2fÅ"%(sc_site_ortho - max_ortho).length(),
           " site_vs_centroid %4.2fÅ"%(sc_site_ortho - centroid).length(),
           " peak_vs_centroid %4.2fÅ"%(max_ortho - centroid).length(),
         )
  print()

  print("============= BEGIN PDB SECTION ==============")
  print("REMARK   3      HETATM records giving the anomalous peak coordinates.")
  print("REMARK   3      Bfactor is populated with the value 100./peak height in sigmas.")
  p = UC.parameters(); sgi = xray_structure.space_group_info()
  print(f"CRYST1{p[0]:9.3f}{p[1]:9.3f}{p[2]:9.3f}{p[3]:7.2f}{p[4]:7.2f}{p[5]:7.2f}",sgi)
  f = UC.fractionalization_matrix()
  print("SCALE1    %10.6f%10.6f%10.6f        0.00000"%f[0:3])
  print("SCALE2    %10.6f%10.6f%10.6f        0.00000"%f[3:6])
  print("SCALE3    %10.6f%10.6f%10.6f        0.00000"%f[6:9])
  for ikey,key in enumerate(result_store):
    print("HETATM%5d"%(1+ikey),key.split('"')[1],
          "  ","%8.3f%8.3f%8.3f"%result_store[key]["peak"].elems," 1.00",
          "%5.2f"%(100./result_store[key]["map_value"]),"%11s"%(result_store[key]["element"]))
  print("TER")
  print("END")
  print("=============   END PDB SECTION ==============")

  from tabulate import tabulate
  data = []
  for atom_pair,L1,L2 in zip (["Mn 1 vs. 4","Mn 1 vs. 3","Mn 3 vs. 4"],[1,1,3],[4,3,4]):
    for monomer in ["A","a"]:
      label1 = 'pdb="MN%1d  OEC %1s 601 "'%(L1,monomer)
      label2 = 'pdb="MN%1d  OEC %1s 601 "'%(L2,monomer)
      drow = [atom_pair,monomer]
      for postype in "site","peak","centroid":
        position1 = result_store[label1][postype]
        position2 = result_store[label2][postype]
        drow.append("%4.2fÅ"%((position1 - position2).length()))
      data.append(drow)
  table = tabulate(
    data,
    headers=["Atom Pair", "Monomer", "Site distance", "Peak distance", "Centroid distance"],
    tablefmt="pipe"
  )
  print(table)
  return result_store

def runplot(xray_structure, selection, real_map, result_store, savepng=False):
  from matplotlib import pyplot as plt
  if savepng:
    import matplotlib
    matplotlib.use('Agg')
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
      label1 = 'pdb="MN%1d  OEC %1s 601 "'%(L1,monomer)
      label2 = 'pdb="MN%1d  OEC %1s 601 "'%(L2,monomer)
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
  if savepng:
            fig.savefig("Mn_transect.png")
            fig.clf()
  else: plt.show()

if __name__ == '__main__':
  xray_structure, selection, real_map, plot, grid5 = run_program(program_class=MyProgram)
  result_store = geometry(xray_structure, selection, real_map, grid5)
  if plot:
    runplot(xray_structure, selection, real_map, result_store, savepng=False)
  else:
    runplot(xray_structure, selection, real_map, result_store, savepng=True)
