"""
Extended version of @idyoung's `plot2.py`, hacked together to plot
two additional horizontal bars for hard-coded stage1 and predict step times.
"""

from __future__ import division
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['figure.figsize'] = [12,8]
outdir=os.path.join('/global/u2/d/dtchon/ECP_plot2/1464625')

def to_min(hr,mn,sc):
    return hr*60 + mn + sc/60.
start = to_min(15,3,30)
untar = to_min(15,5,9) - start

class Tranche:
  def __init__(self,
               protein='Cry11Ba',
               prodir='cry11ba',
               projob=0,
               prolen=16,
               s1_time=1.0,
               pr_time=1.0):
    tranche_err = os.path.join(outdir,prodir+"_job%d.err"%projob)
    print(tranche_err)
    with open(tranche_err,"r") as K:
      errlines = K.readlines()
    self.meta = self.get_meta(errlines) - start
    self.runstart = self.get_runstart(errlines) - start
    self.back = self.get_back(errlines) - start
    self.gpu = self.get_gpu(errlines) - start
    self.last, self.n_last = self.get_last_iteration(errlines)
    self.last = self.last-start
    events = self.get_events(errlines)
    self.events = [e-start for e in events]
    lightblue1 = "#6fa8dc"
    self.pcolors = {'cry11ba':lightblue1,'cyto':"#8e7cc3",'thermo':"#c27ba0",'yb_lyso':"#ffd966"}
    self.dcolors = {'cry11ba':"#3f78ac",'cyto':"#5e4c93",'thermo':"#924b70",'yb_lyso':"#cfa936"}
    self.prodir = prodir
    self.protein = protein
    self.prolen = self.get_prolen_str(prolen)
    self.s1_time = -s1_time
    self.pr_time = -pr_time
  def get_prolen_str(self, prolen):
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
  def get_meta(self,lines):
    for line in lines:
        text = line.strip().split()
        if len(text)>=9 and " ".join(text[6:9])=="LOADING ROI DATA":
            return to_min(int(text[3][0:2]),int(text[3][3:5]),int(text[3][6:8]))

  def get_runstart(self,lines):
    text = lines[0].strip().split()
    return to_min(int(text[3][0:2]),int(text[3][3:5]),int(text[3][6:8]))

  def get_back(self,lines):
    for line in lines:
      text = line.strip().split()
      if len(text)>=10 and " ".join(text[5:10])=="DONE LOADING DATA; EXIT BARRIER":
            return to_min(int(text[3][0:2]),int(text[3][3:5]),int(text[3][6:8]))

  def get_gpu(self,lines):
    for line in lines:
      text = line.strip().split()
      if len(text)>=6 and text[5]=="Iterate":
            return to_min(int(text[3][0:2]),int(text[3][3:5]),int(text[3][6:8]))

  def get_last_iteration(self,lines):
    for line in lines:
      text = line.strip().split()
      if "iteration" in text: myline = text
    clock = to_min(int(myline[3][0:2]),int(myline[3][3:5]),int(myline[3][6:8]))
    itno = myline[10]
    return clock,itno

  def get_events(self,lines):
    events=[]
    for line in lines:
      text = line.strip().split()
      if "iteration" in text and int(text[10])%100==0:
        clock = to_min(int(text[3][0:2]),int(text[3][3:5]),int(text[3][6:8]))
        events.append(clock)
    return events

def tranches():
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=4,prolen=2,s1_time=48.000,pr_time=31.467)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=3,prolen=5,s1_time=66.067,pr_time=30.800)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=2,prolen=10,s1_time=206.53,pr_time=30.5003)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=1,prolen=25,s1_time=240.76,pr_time=33.1337)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=0,prolen=40,s1_time=180.00,pr_time=31.7670)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=4,prolen=0.5,s1_time=45.700,pr_time=54.533)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=3,prolen=2,s1_time=300.40,pr_time=49.2000)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=2,prolen=4,s1_time=300.41,pr_time=48.9677)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=1,prolen=8,s1_time=86.033,pr_time=55.333)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=0,prolen=16,s1_time=177.05,pr_time=55.3170)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=4,prolen=1,s1_time=25.783,pr_time=14.800)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=3,prolen=2,s1_time=43.450,pr_time=25.167)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=2,prolen=5,s1_time=57.800,pr_time=25.233)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=1,prolen=10,s1_time=66.467,pr_time=25.367)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=0,prolen=20,s1_time=64.133,pr_time=21.683)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=4,prolen=.125,s1_time=30.367,pr_time=28.917)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=3,prolen=.25,s1_time=46.767,pr_time=45.175)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=2,prolen=.5,s1_time=52.867,pr_time=47.325)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=1,prolen=1,s1_time=55.567,pr_time=47.908)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=0,prolen=2,s1_time=55.483,pr_time=47.283)

def run():
  fig, ax = plt.subplots(height_ratios=[0.9])
  data = [d for d in tranches()]
  people = tuple(['%s, %s μm'%(d.protein, d.prolen) for d in data])
  y_pos = np.arange(1,1+len(people))
  for idata,d in enumerate(data):
    ax.barh([y_pos[idata]],[d.last],color=d.get_pcolor(),align='center',
        label=f"$F_h$ estimation, {d.protein}" \
                if idata % 5 == 0 else '_nolegend_')
    ax.eventplot(positions=d.events, lineoffsets=y_pos[idata], linelengths=0.10,
        color=d.get_dcolor(), label='_nolegend_')
    ax.annotate(f'$F_h$ estimation: {d.n_last} iters',
        xy=(0.9, idata*0.048 + 0.03), xycoords='axes fraction')
    ax.barh([y_pos[idata]], [d.gpu], color='#E0E0E0', align='center',
        label="Set up GPU workspace" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.back], color='orange', align='center',
        label="Read data, refine background" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.meta], color='yellow', align='center',
        label="Read metadata" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.runstart], color='green', align='center',
        label="Run Python" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [untar], color='#606060', align='center',
        label="Untar the executable" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.pr_time],
            color='xkcd:wheat', align='center',
            label="Predict step" if idata == 0 else '_nolegend_')
    ax.barh([y_pos[idata]], [d.s1_time], left=d.pr_time,
            color='xkcd:tan', align='center',
            label="Stage 1 step" if idata == 0 else '_nolegend_')
  ax.annotate("Sets of 100 iterations",
    xy=(0.825, 0.85), xycoords='axes fraction',
    xytext=(-80,20), textcoords='offset points',
    arrowprops=dict(arrowstyle="simple", fc="0.2", ec="none"))
  ax.set_yticks(y_pos, labels=people)
  ax.tick_params(left=False)
  ax.invert_yaxis()  # labels read top-to-bottom
  ax.set_xlabel('Wall clock time (min)')
  ax.set_xlim(-400,150)
  ax.set_ylim(0.2,1+len(people))
  ax.set_title('Full scale SLURM job, 5120 nodes, 20x4096 MPI ranks')
  handles, labels = plt.gca().get_legend_handles_labels()
  handles = handles[1:][::] #+ ([handles[0]] + handles[6:])[::-1]
  labels = labels[1:][::] #+ ([labels[0]] + labels[6:])[::-1]
  ax.legend(handles, labels)
  plt.tight_layout()
  plt.show()

if __name__=="__main__":
  run()