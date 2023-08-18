import sys
import pickle
import numpy as np
from matplotlib import pyplot as plt

plt.rcParams["axes.prop_cycle"] = plt.cycler("color", plt.cm.tab20.colors)

def load_pickle(slurm_id, rank):
    with open(f"timestamps_{slurm_id}.pkl", 'rb') as F:
        times = pickle.load(F)

    for label in times:
        timepoints = times[label]
        times[label] = {"points":timepoints, "ranks":len(timepoints)*[rank]}
    return times

if __name__=="__main__":
    times = {}
    slurm_ids = [int(s) for s in sys.argv[1:]]
    slurm_ids = sorted(slurm_ids)
    for i,slurm_id in enumerate(slurm_ids):
        timepoints = load_pickle(slurm_id, i)
        for label in timepoints:
            if label not in times:
                times[label] = {"points":[], "ranks":[]}
            for sublabel in timepoints[label]:
                times[label][sublabel] += timepoints[label][sublabel]

    max_time = 0

    for label in times:
        times[label]['points'] = np.array(times[label]['points']) / 60
        max_time = max(max_time, max(times[label]['points']))
        print_label = label
        while len(print_label)>0 and print_label[0] == "_":
            print_label = print_label[1:]
        plt.plot(times[label]["points"], times[label]["ranks"], 'o', label=print_label)

    plt.yticks(range(len(slurm_ids)), slurm_ids)
    plt.ylabel("Slurm ID")
    plt.xlabel("Time since job start [min]")
    plt.title("yb_lyso_100k_stage2")
    plt.xlim(0, max_time)
    plt.legend()
    plt.show()
