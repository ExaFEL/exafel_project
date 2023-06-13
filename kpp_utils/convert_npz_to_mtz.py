"""
Convert the .npz output of simtbx.diffBragg.stage_two to .mtz
"""

import numpy as np

INPUT_PATH = '.'
f_asu_map=np.load(INPUT_PATH + '/f_asu_map.npy',allow_pickle=True)[()]
d=np.load('_fcell_trial0_iter484.npz')
f=d['fvals']


diffbragg utils to convert to mtz

from dials.array_family import flex
flex.array(d)

map_hkl_list(Hi_lst, anomalous_flag=True, symbol="P43212")



miller_idx = [f_asu_map[i] for i in range(len(f))]

miller_idx = flex.miller_index([f_asu_map[i] for i in range(len(f))])

from cctbx import miller, crystal

cs = crystal.symmetry((78,78,264,90,90,120),'P6522')

mset = miller.set(cs, miller_idx, True)

mdat = flex.double(f)
ma = miller.array(mset,mdat)
ma.is_xray_amplitude_array()

ma = ma.set_observation_type_xray_amplitude()

ma.as_mtz_dataset(column_root_label='F').mtz_object().write('test.mtz')

ctrl-z
iotbx.mtz.dump test.mtz

iotbx.fetch_pdb 5wp2



ipython
foreground
fg


from simtbx.diffBragg.utils import get_complex_fcalc_from_pdb

ma_calc = get_complex_fcalc_from_pdb('5wp2.pdb',wavelength=1.3,dmin=1.6,dmax=60).as_amplitude_array()

ma_map={h:v for h,v in zip(ma.indices(),ma.data())}
hm_comm = set(ma_calc_map).intersection(set(ma_map))

val_0 = [ma_map[h] for h in hm_comm]
val_1 = [ma_calc_map[h] for h in hm_comm]

from scipy.stats import pearsonr
pearsonr(val_0,val_1)

100shuff.mtz
*mtz from iter0 and mtz from iter1

from matplotlib import pyplot as plt
plt.scatter(val_0, val_1)

plt.loglog(val_0, val_1)  # to make logarithmic axes

load mtz

fastbins: turn kokkos flag off and run 2 shot test

correlation converged around 90
plot as a function of iteration