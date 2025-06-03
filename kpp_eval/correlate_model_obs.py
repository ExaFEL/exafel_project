"""
Usage:
libtbx.python correlate_model_obs.py \
$MODULES/ls49_big_data/7RF1_refine_030_Aa_refine_032_refine_034.pdb \
/global/cfs/cdirs/m3562/users/dtchon/p20231/common/ensemble1/SPREAD2l/v000/SPREAD2l_v000_all.mtz \
miller_array.labels.name="Iobs" \
xray_data.high_resolution=3.0
"""
from __future__ import division, print_function
import sys
from libtbx.str_utils import make_sub_header
from libtbx.utils import Sorry
from scitbx.array_family import flex
from iotbx.cli_parser import run_program
from libtbx.program_template import ProgramTemplate

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

    print("Have data manager")
    F = self.fmodel.f_model()
    Imodel = F.as_intensity_array() #734952
    print ("Imodel",Imodel.size())

    dm = self.data_manager
    mtz_arrays = dm.get_miller_arrays()
    Iobs = mtz_arrays[0]
    print ("Iobs",Iobs.size()) #741164

    from cctbx.miller import match_indices
    matches = match_indices(Iobs.indices(), Imodel.indices())
    print("Number of matches",len(matches.pairs())) #734952
    Iobs_plot = Iobs.data().select(matches.pairs().column(0))
    Imod_plot = Imodel.data().select(matches.pairs().column(1))
    F = flex.linear_correlation(Iobs_plot,Imod_plot)
    print("Pearson correlation",F.coefficient())
    G = flex.linear_regression(Iobs_plot,Imod_plot)
    G.show_summary()

    from matplotlib import pyplot as plt
    plt.hist2d(Iobs_plot,Imod_plot,bins=(200,200),range=[[-50000,500000],[0,500000]])
    plt.colorbar()
    plt.plot([0,5.E5],[0,5.E5],'k-',label="unit slope")
    plt.plot([0,5.E5],[G.y_intercept(),G.y_intercept() + G.slope() * 5.E5], label="regression_slope")
    plt.title(f"Correlation of Iobs from MTZ and Imodel from PDB")
    plt.xlabel("Iobs")
    plt.ylabel("Imodel")
    plt.legend(loc='lower right')
    #from IPython import embed; embed()
    plt.show()

  # ---------------------------------------------------------------------------
  def get_results(self):
    '''
    The thing to be returned
    '''
    return None

if __name__ == '__main__':
  run_program(program_class=MyProgram)
