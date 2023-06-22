"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz
"""

import numpy as np
import os
from matplotlib import pyplot as plt
from scipy.stats import pearsonr
import glob
import iotbx.mtz
from dials.array_family import flex
from cctbx import miller, crystal
from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb
from LS49 import ls49_big_data
big_data = ls49_big_data
def full_path(filename):
  return os.path.join(big_data,filename)

def npz_to_mtz(npz_path, 
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
    # ma.is_xray_amplitude_array()
    ma = ma.set_observation_type_xray_amplitude()
    # print(npz_path, ma.size(), np.max(ma.data()), np.mean(ma.data()), np.std(ma.data()))
    if save_mtz:
        ma.as_mtz_dataset(column_root_label='F').mtz_object().write(npz_path + '.mtz')
    return ma


def evaluate_iter(ma,
                  ma_proc, # output from conventional merging
                  ma_calc, # ground truth structure factors
                  show_fig=False,
                 ):
    ma_map={h:v for h,v in zip(ma.indices(),ma.data())}
    ma_calc_map={h:v for h,v in zip(ma_calc.indices(),ma_calc.data())}
    ma_proc_map={h:v for h,v in zip(ma_proc.indices(),ma_proc.data())}

    hm_comm = set(ma_calc_map).intersection(set(ma_map))
    hm_comm = hm_comm.intersection(set(ma_proc_map))

    val_0 = [ma_map[h] for h in hm_comm]
    ground_truth = [ma_calc_map[h] for h in hm_comm]

    pearson_coeff = pearsonr(val_0,ground_truth)
    print('Pearson correlation coefficient: ', pearson_coeff[0])

    if show_fig:
        plt.figure()
        plt.scatter(val_0, ground_truth)
        plt.show()

        plt.figure()
        plt.scatter(np.log(val_0), np.log(ground_truth))  # to make logarithmic axes
        plt.show()

    return pearson_coeff, val_0, ground_truth


if __name__=='__main__':
    unit_cell = (67.2, 59.8, 47.2, 90, 110.3, 90)
    space_group = 'C121'

    # path to output of diffBragg stage 2
    input_path = os.environ["WORK"] + 'diffbragg_stage2/10217122'
    # output of conventional merging mtz file
    mtz_path = os.environ["SCRATCH"] + "/ferredoxin_sim/9521300/out/ly99sim_all.mtz" # output of conventional merging
    # Ground truth structure factors
    ma_calc = get_complex_fcalc_from_pdb(full_path("1m2a.pdb"),wavelength=1.3,dmin=1.9,dmax=1000).as_amplitude_array()

    # Miller index map
    f_asu_map=np.load(input_path + '/f_asu_map.npy',allow_pickle=True)[()]

    # Output of conventional merging
    ma_proc = iotbx.mtz.object(mtz_path).as_miller_arrays()[0]
    ma_proc = ma_proc.as_amplitude_array()
    pearson_coeff, val_0, ground_truth = evaluate_iter(ma_proc, ma_proc, ma_calc)
    
    all_iter_npz = len(glob.glob(input_path + '/_fcell_trial0_iter*.npz'))

    pearson_coeff_vec = [pearson_coeff.statistic]
    for num_iter in range(all_iter_npz):
        npz_file = input_path + '/_fcell_trial0_iter' + str(num_iter)
        print(npz_file)
        ma = npz_to_mtz(npz_file,                
                        f_asu_map,
                        unit_cell,
                        space_group,
                        save_mtz=True,
                        )
        # import IPython
        # IPython.embed()
        pearson_coeff, val_0, ground_truth = evaluate_iter(ma, ma_proc, ma_calc)
        pearson_coeff_vec.append(pearson_coeff.statistic)

    # Plot pearson_coeff as a function of iteration
    plt.figure()
    plt.plot(pearson_coeff_vec,".")
    plt.savefig('pearson_coeff.png')
    plt.show()