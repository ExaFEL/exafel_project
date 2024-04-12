from __future__ import division

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.legend_handler import HandlerTuple
import numpy as np
import pandas as pd

plt.rcParams['figure.figsize'] = [10, 5]
with open('./128ki_timestamps2.csv', 'r') as file:
  date_columns = ['stage1_start', 'stage1_stop', 'predict_start',
                  'predict_stop', 'stage2_start', 'stage2_stop']
  table = pd.read_csv(file, index_col=0, parse_dates=date_columns)

cm = plt.cm.get_cmap('tab20c')


class Tranche:
  def __init__(self, protein='Cry11Ba', prodir='cry11ba', prolen=16):
    self.index = prodir + '_128Kimg_' + self.get_prolen_str(prolen) + 'um'
    self.stage1_start = table.loc[self.index, 'stage1_start']
    self.predict_start = table.loc[self.index, 'predict_start']
    self.stage2_start = table.loc[self.index, 'stage2_stop']
    self.stage1_stop = table.loc[self.index, 'stage1_stop']
    self.predict_stop = table.loc[self.index, 'predict_stop']
    self.stage2_stop = table.loc[self.index, 'stage2_stop']
    self.s1m = table.loc[self.index, 'stage1_delta'] / 60
    self.prm = table.loc[self.index, 'predict_delta'] / 60
    self.s2m = table.loc[self.index, 'stage2_delta'] / 60
    self.iters = table.loc[self.index, '2h_iters']
    self.events = np.arange(self.s1m + self.prm,
                            self.s1m + self.prm + self.s2m,
                            100 * self.s2m / self.iters)

    self.s1_color = cm({'yb_lyso': 2, 'thermo': 6, 'cry11ba': 10, 'cyto': 14}[prodir])
    self.pr_color = cm({'yb_lyso': 1, 'thermo': 5, 'cry11ba': 9, 'cyto': 13}[prodir])
    self.s2_color = cm({'yb_lyso': 0, 'thermo': 4, 'cry11ba': 8, 'cyto': 12}[prodir])

    self.pcolors = {'cry11ba':"#6fa8dc",'cyto':"#8e7cc3",'thermo':"#c27ba0",'yb_lyso':"#ffd966"}
    self.dcolors = {'cry11ba':"#3f78ac",'cyto':"#5e4c93",'thermo':"#924b70",'yb_lyso':"#cfa936"}
    self.prodir = prodir
    self.protein = protein
    self.prolen = self.get_prolen_str(prolen)

  @staticmethod
  def get_prolen_str(prolen):
    p = float(prolen)
    if f'{p:.0f}.000' == f'{p:.3f}':
      return f'{p:.0f}'
    elif f'{p:.1f}00' == f'{p:.3f}':
      return f'{p:.1f}'
    elif f'{p:.2f}0' == f'{p:.3f}':
      return f'{p:.2f}'
    else:
      return f'{p:.3f}'

  def get_pcolor(self): return self.pcolors[self.prodir]
  def get_dcolor(self): return self.dcolors[self.prodir]

def tranches():
  yield Tranche(protein='Cytochrome',prodir='cyto', prolen=40)
  yield Tranche(protein='Cytochrome',prodir='cyto', prolen=2)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba', prolen=16)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba', prolen=0.5)
  yield Tranche(protein='Thermolysin',prodir='thermo', prolen=20)
  yield Tranche(protein='Thermolysin',prodir='thermo', prolen=1)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso', prolen=2)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso', prolen=.125)

def run():
  fig, ax = plt.subplots(height_ratios=[0.9])
  data = [d for d in tranches()]
  people = tuple(['%s, %s μm'%(d.protein, d.prolen) for d in data])
  y_pos = np.arange(1,1+len(people))
  for idata, d in enumerate(data):
    ax.text(d.s1m + d.prm + d.s2m + 1, y_pos[idata], f"{d.iters} iters", va='center')
    ax.eventplot(positions=d.events, lineoffsets=y_pos[idata],
                 linelengths=0.20, color=d.s1_color, label='_nolegend_')
    #ax.annotate(f'$F_h$ estimation: {d.n_last} iters',
    #    xy=(d.events[0]*0.009, idata*0.048 + 0.03), xycoords='axes fraction')
    ax.barh([y_pos[idata]], [d.s1m + d.prm, d.s1m + d.prm + d.s2m],
            color=d.s2_color, align='center',
            label="Stage 2" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.s1m, d.s1m + d.prm],
            color=d.pr_color, align='center',
            label="Predict" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [0, d.s1m],
            color=d.s1_color, align='center',
            label="Stage 1" if idata == 0 else '_nolegend_')
  #ax.annotate("Sets of 100 iterations",
  #  xy=(0.8, 0.715), xycoords='axes fraction',
  #  xytext=(-20,20), textcoords='offset points',
  #  arrowprops=dict(arrowstyle="simple", fc="0.2", ec="none"))
  ax.set_yticks(y_pos, labels=people)
  ax.tick_params(left=False)
  ax.invert_yaxis()  # labels read top-to-bottom
  ax.set_xlabel('Wall clock time (min)')
  ax.set_xlim(-2, 172)
  ax.set_ylim(0.2,1+len(people))
  ax.set_title('Perlmutter 1/4 scale SLURM job, 8 Tranches x 128 nodes, 8 Tranches x 4096 MPI ranks')
  handles, labels = plt.gca().get_legend_handles_labels()
  s1_handles = [mpatches.Patch(facecolor=cm(i)) for i in (2, 6, 10, 14)]
  pr_handles = [mpatches.Patch(facecolor=cm(i)) for i in (1, 5, 9, 13)]
  s2_handles = [mpatches.Patch(facecolor=cm(i)) for i in (0, 4, 8, 12)]
  handles = [s1_handles, pr_handles, s2_handles]
  labels = labels[0:4][::-1] #+ ([labels[0]] + labels[6:])[::-1]
  ax.legend(handles, labels, handler_map = {list: HandlerTuple(None)},
            handlelength=8)
  plt.tight_layout()
  plt.show()

if __name__=="__main__":
  run()
