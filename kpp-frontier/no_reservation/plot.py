from __future__ import division
import matplotlib.pyplot as plt
import numpy as np
import os
plt.rcParams['figure.figsize'] = [12,8]
#jobid="1462681" # earlier trial does not plot
jobid="1464625"
outdir=os.path.join("/lustre/orion/chm137/proj-shared/cctbx/no_reservation",jobid)

def to_min(hr,mn,sc):
    return hr*60 + mn + sc/60.
start = to_min(15,3,30)
untar = to_min(15,5,9) - start

class Tranche:
  def __init__(self,protein='Cry11Ba',prodir='cry11ba',projob=0,prolen=16):
    tranche_err = os.path.join(outdir,prodir+"_job%d.err"%projob)
    print(tranche_err)
    with open(tranche_err,"r") as K:
      errlines = K.readlines()
    print("A")
    self.meta = self.get_meta(errlines) - start
    print("B")
    self.runstart = self.get_runstart(errlines) - start
    print("C")
    self.back = self.get_back(errlines) - start
    print("D")
    self.gpu = self.get_gpu(errlines) - start
    print("E")
    self.last, self.n_last = self.get_last_iteration(errlines)
    self.last = self.last-start
    print("F")
    events = self.get_events(errlines)
    print("G")
    self.events = [e-start for e in events]
    lightblue1 = "#6fa8dc"
    self.pcolors = {'cry11ba':lightblue1,'cyto':"#8e7cc3",'thermo':"#c27ba0",'yb_lyso':"#ffd966"}
    self.dcolors = {'cry11ba':"#3f78ac",'cyto':"#5e4c93",'thermo':"#924b70",'yb_lyso':"#cfa936"}
    self.prodir = prodir
    self.protein = protein
    self.prolen = prolen
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
      if len(text)>=8 and " ".join(text[5:8])=="DONE LOADING DATA;":
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
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=4,prolen=2)
  print(1)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=3,prolen=5)
  print(1)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=2,prolen=10)
  print(1)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=1,prolen=25)
  print(1)
  yield Tranche(protein='Cytochrome',prodir='cyto',projob=0,prolen=40)
  print(1)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=4,prolen=0.5)
  print(1)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=3,prolen=2)
  print(1)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=2,prolen=4)
  print(3)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=1,prolen=8)
  print(1)
  yield Tranche(protein='Cry11Ba',prodir='cry11ba',projob=0,prolen=16)
  print(1)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=4,prolen=1)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=3,prolen=2)
  print(1)
  print(2)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=2,prolen=5)
  print(9)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=1,prolen=10)
  print(1)
  yield Tranche(protein='Thermolysin',prodir='thermo',projob=0,prolen=20)
  print(4)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=4,prolen=.125)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=3,prolen=.25)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=2,prolen=.5)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=1,prolen=1)
  yield Tranche(protein='Lysozyme',prodir='yb_lyso',projob=0,prolen=2)

def run():
  fig, ax = plt.subplots(height_ratios=[0.9])
  data = [d for d in tranches()]
  people = tuple(['%s, %.1f μm'%(d.protein, float(d.prolen)) for d in data])
  y_pos = np.arange(1,1+len(people))
  for idata,d in enumerate(data):
    ax.barh([y_pos[idata]],[d.last],color=d.get_pcolor(),align='center',
          label="$F_h$ estimation, %s iterations"%(d.n_last))
    ax.eventplot(positions=d.events,lineoffsets=y_pos[idata],linelengths=0.90,color=d.get_dcolor())
    ax.barh([y_pos[idata]], [d.gpu], color='#E0E0E0', align='center', label="Set up GPU workspace")
    ax.barh([y_pos[idata]], [d.back], color='brown', align='center', label="Read data, refine background")
    ax.barh([y_pos[idata]], [d.meta], color='yellow', align='center', label="Read metadata")
    ax.barh([y_pos[idata]], [d.runstart], color='green', align='center', label="Run Python")
    ax.barh([y_pos[idata]], [untar], color="red", align='center', label="Untar the executable")
  ax.set_yticks(y_pos, labels=people)
  ax.invert_yaxis()  # labels read top-to-bottom
  ax.set_xlabel('Wall clock time (min)')
  ax.set_xlim(-2,122)
  ax.set_ylim(0.2,1+len(people))
  ax.set_title('Full scale SLURM job, 5120 nodes, 20x4096 MPI ranks')
  plt.tight_layout()
  plt.show()

if __name__=="__main__":
  run()
