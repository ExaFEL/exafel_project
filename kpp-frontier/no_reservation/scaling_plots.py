from libtbx import easy_pickle
from matplotlib import pyplot as plt
from matplotlib import ticker

def get_colorlist():
  #colorlist = ["bright lilac", "pure blue", "greenish blue", "dark mint green", "green yellow", "sunflower yellow", "tangerine", "cerise"]
  colorlist = ["greenish blue",
               "dark mint green",
               #"green yellow",
			   "sunflower yellow",
			   "tangerine",
			   "cerise"]
  colorlist = colorlist + colorlist
  colorlist = ["xkcd:" + color for color in colorlist]
  return colorlist

def get_scalable_walltime(jobid, niters=100):
  print(f"analyzing job {jobid}...")
  data = easy_pickle.load(f"{jobid}.pkl")
  scalable_time_start = data['EVENT: launch refiner'][0]
  print(f"start: {scalable_time_start}")
  scalable_time_end = data['DONE WITH FUNC GRAD'][niters]
  print(f"end ({niters} iterations): {scalable_time_end}")
  duration = scalable_time_end - scalable_time_start
  print(f"duration: {duration}\n")
  return duration

def plot_scaling(measured_series_dict, ideal_series_dict, xlabel, ylabel, title,
                 ymin=None, xmin=None, logx=True, logy=True, extra={},
                 legend_loc="lower left"):
  colorlist = get_colorlist()
  fig, ax = plt.subplots()
  for label, (xdata, ydata) in measured_series_dict.items():
    ax.plot(xdata, ydata, label=label,
            color=colorlist.pop(0), marker="s", linestyle="-")
  for label, (xdata, ydata, color, marker, style) in extra.items():
    ax.plot(xdata, ydata, label=label,
            color=color, marker=marker, linestyle=style)
  for label, (xdata, ydata) in ideal_series_dict.items():
    ax.plot(xdata, ydata, label=label,
            color=colorlist.pop(0), marker=None, linestyle="--")
  if logx: ax.set_xscale('log',base=10)
  if logy: ax.set_yscale('log',base=10)
  if xmin is not None: ax.set_xlim((xmin, None))
  if ymin is not None: ax.set_ylim((ymin, None))
  ax.set_xlabel(xlabel)
  ax.set_ylabel(ylabel)
  ax.legend(loc=legend_loc)
  plt.title(title)
  plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
  plt.gca().yaxis.set_minor_formatter(ticker.ScalarFormatter())
  plt.gca().xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:n}"))
  plt.gca().xaxis.set_minor_formatter(ticker.ScalarFormatter())
  plt.show()

strong_65k_jobids = [1479720, 1479721, 1479723, 1479724]
strong_65k_nnodes = [32, 64, 128, 256]
strong_65k_ideal_times = [400, 200, 100, 50]

strong_524k_jobids = [1481182, 1480353]
strong_524k_nnodes = [256, 128]
strong_524k_ideal_times = [400, 800]

def plot_strong_scaling():
  niters=98
  strong_65k_times = [get_scalable_walltime(jobid, niters=niters) \
    for jobid in strong_65k_jobids]
  strong_524k_times = [get_scalable_walltime(jobid, niters=niters) \
    for jobid in strong_524k_jobids]
  meas_series_dict = {
    "Lysozyme, 2$\mu$m crystals, 65k images":
	  (strong_65k_nnodes, strong_65k_times),
	"Lysozyme, 2$\mu$m crystals, 524k images":
      (strong_524k_nnodes, strong_524k_times)
  }
  extra = {
    "Lysozyme, 2$\mu$m crystals, full scale test":
      (full_scale_nnodes, get_scalable_walltime(full_scale_jobid, niters=niters), "red", ".", "")
  }
  ideal_series_dict = {
    "Ideal strong scaling":
      (strong_65k_nnodes, [t*niters/100 for t in strong_65k_ideal_times])
  }
  plot_scaling(meas_series_dict, ideal_series_dict, extra=extra,
               xlabel="Nodes requested",
               ylabel="Scalable wall time (s)",
               title=f"Strong scaling on $F_h$ estimation, {niters} iterations",
               legend_loc="lower left")

full_scale_jobid = 1464625
full_scale_nimg = 524199
full_scale_nnodes = 256
weak_scaling_jobids = [1479717, 1479718, 1479719, 1479720]
weak_scaling_nimg = [524199, 262000, 131000, 65500]
weak_scaling_nnodes = [256, 128, 64, 32]
weak_scaling_ideal_time = 360

def plot_weak_scaling():
  weak_scaling_times = [get_scalable_walltime(jobid, niters=100) \
    for jobid in weak_scaling_jobids]
  weak_scaling_rates = [nimg/nsec for (nimg, nsec) in \
    zip(weak_scaling_nimg, weak_scaling_times)]
  meas_series_dict = {
    "Lysozyme, 2$\mu$m crystals, 2046 images per node":
      (weak_scaling_nnodes, weak_scaling_rates)
  }
  extra = {
    "Lysozyme, 2$\mu$m crystals, full scale test":
      (full_scale_nnodes, full_scale_nimg/get_scalable_walltime(full_scale_jobid, niters=100), "red", ".", "")
  }
  ideal_scaling_rates = [nimg/weak_scaling_ideal_time \
    for nimg in weak_scaling_nimg]
  ideal_series_dict = {
    "Ideal weak scaling":
      (weak_scaling_nnodes, ideal_scaling_rates)
  }
  plot_scaling(meas_series_dict, ideal_series_dict, extra=extra,
               xlabel="Nodes requested",
               ylabel="Data throughput (images per second)",
               title="Weak scaling on $F_h$ estimation, 100 iterations",
               legend_loc="lower right")

if __name__ == "__main__":
  plot_weak_scaling()
  plot_strong_scaling()

