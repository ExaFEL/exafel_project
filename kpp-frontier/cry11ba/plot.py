from __future__ import division
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['figure.figsize'] = [12,2]

fig, ax = plt.subplots(height_ratios=[0.9])

people = ('', 'Cry11Ba, 16.0 μm')
y_pos = np.arange(len(people))
performance = [0,120]

lightblue1 = "#6fa8dc"

ax.barh(y_pos, performance, color=lightblue1, align='center', label="$F_h$ estimation, 304 iterations")
iter100 = 8*60 + 22 + 5./60 - (7*60 + 35 + 38./60)
iter200 = 8*60 + 58 + 40./60 - (7*60 + 35 + 38./60)
iter300 = 9*60 + 33 + 54./60 - (7*60 + 35 + 38./60)
ax.eventplot(positions=[iter100,iter200,iter300])
ax.barh(y_pos, [0, 655./60], color='#E0E0E0', align='center', label="Set up GPU workspace")
ax.barh(y_pos, [0, 627./60], color='brown', align='center', label="Read data, refine background")
ax.barh(y_pos, [0, 102./60], color='yellow', align='center', label="Read metadata")
ax.barh(y_pos, [0, 83./60], color='green', align='center', label="Run Python")
ax.barh(y_pos, [0,73./60], color="red", align='center', label="Untar the executable")
ax.set_yticks(y_pos, labels=people)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel('Wall clock time (min)')
ax.set_xlim(-2,122)
ax.set_ylim(0.2,3.5)
ax.set_title('Single-tranche SLURM job, 256 nodes, 4096 MPI ranks')
ax.legend(ncols=3,reverse=True)
plt.tight_layout()
plt.show()
