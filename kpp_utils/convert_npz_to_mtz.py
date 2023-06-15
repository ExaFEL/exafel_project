"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz
"""

import numpy as np
import os
from matplotlib import pyplot as plt
from scipy.stats import pearsonr
from dials.array_family import flex
from cctbx import miller, crystal
from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb
from LS49 import ls49_big_data
big_data = ls49_big_data
def full_path(filename):
  return os.path.join(big_data,filename)

def evaluate_iter(npz_path,
                  ma_calc_map,
                  f_asu_map,
                  unit_cell,
                  space_group,
                  save_mtz=False,
                  ):
    d=np.load(npz_path + '.npz')
    f=d['fvals']

    miller_idx = flex.miller_index([f_asu_map[i] for i in range(len(f))])

    cs = crystal.symmetry(unit_cell,space_group)
    mset = miller.set(cs, miller_idx, True)
    mdat = flex.double(f)
    ma = miller.array(mset,mdat)
    ma.is_xray_amplitude_array()
    ma = ma.set_observation_type_xray_amplitude()
    if save_mtz:
        ma.as_mtz_dataset(column_root_label='F').mtz_object().write(npz_path + '.mtz')
    ma_map={h:v for h,v in zip(ma.indices(),ma.data())}

    hm_comm = set(ma_calc_map).intersection(set(ma_map))

    val_0 = [ma_map[h] for h in hm_comm]
    ground_truth = [ma_calc_map[h] for h in hm_comm]

    pearson_coeff = pearsonr(val_0,ground_truth)
    print('Pearson correlation coefficient: ', pearson_coeff[0])

    plt.figure()
    plt.scatter(val_0, ground_truth)
    plt.show()

    plt.figure()
    plt.loglog(val_0, ground_truth)  # to make logarithmic axes
    plt.show()

    return pearson_coeff, val_0, ground_truth


if __name__=='__main__':
    unit_cell = (67.2, 59.8, 47.2, 90, 110.3, 90)
    space_group = 'C121'

    # get environment variable WORK
    input_path = os.environ["WORK"] + 'diffbragg_stage2/10211797'

    # Ground truth structure factors
    ma_calc_map = get_complex_fcalc_from_pdb(full_path("1m2a.pdb"),wavelength=1.3,dmin=1.6,dmax=60).as_amplitude_array()

    # Miller index map
    f_asu_map=np.load(input_path + '/f_asu_map.npy',allow_pickle=True)[()]


    npz_path = os.environ["SCRATCH"] + "/ferredoxin_sim/9521300/out/ly99sim_all.mtz" # output of conventional merging
    pearson_coeff, val_0, ground_truth = evaluate_iter(npz_path,
                                                       ma_calc_map,
                                                       f_asu_map,
                                                       unit_cell,
                                                       space_group,
                                                      )
    
    all_iter_npz = np.sort(glob.glob(input_path + '/_fcell_trial0_iter*.npz'))
    for npz_file in all_iter_npz:
        pearson_coeff, val_0, ground_truth = evaluate_iter(npz_file,
                                                           ma_calc_map,
                                                           f_asu_map,
                                                           unit_cell,
                                                           space_group,
                                                           save_mtz=True,
                                                          )