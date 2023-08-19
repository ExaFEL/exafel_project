"""
Calculate the timing of individual diffBragg stage2 steps using general or
per-node log files with event timestamps. Based on work by Felix Wittwer.
"""
from datetime import datetime
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Iterable, List, NamedTuple, Tuple, Union

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from exafel_project.kpp_eval.phil import parse_phil


phil_scope_str = """
stage2
  .multiple = True
{
  err = None
    .type = str
    .help = Glob to JOB_ID.err or individual node ranks "mainLog"s containing
    .help = timestamps of individual events. If None, all files in current
    .help = directory will be read.
  out = None
    .type = str
    .help = Glob to JOB_ID.out containing "jobstart" and "jobend" timestamps.
    .help = If None, first/last event time will be used as start/end date.
}
"""

class EventKind(NamedTuple):
  log_string: str
  color_idx: int

  @property
  def color(self):
    return plt.cm.tab20.colors[self.color_idx % 20]

  @property
  def handle(self):
    return Line2D([], [], color=self.color, marker='o',
                  label=self.log_string.lstrip('_'))

event_kinds = [
  EventKind('EVENT: read input pickle', 0),
  EventKind('EVENT: BEGIN prep dataframe', 1),
  EventKind('EVENT: DONE prep dataframe', 2),
  EventKind('EVENT: begin loading inputs', 3),
  EventKind('EVENT: BEGIN loading experiment list', 4),
  EventKind('EVENT: DONE loading experiment list', 5),
  EventKind('EVENT: LOADING ROI DATA', 6),
  EventKind('EVENT: DONE LOADING ROI', 7),
  EventKind('EVENT: Gathering global HKL information', 8),
  EventKind('EVENT: FINISHED gather global HKL information', 9),
  EventKind('EVENT: launch refiner', 10),
  EventKind('DONE WITH FUNC GRAD', 11),
  EventKind('_launcher done running optimization', 12),
]
event_kind_registry = {et.log_string: et for et in event_kinds}


@dataclass
class Event:
  kind: EventKind
  date: datetime
  node: int
  rank: int

  @classmethod
  def from_log_line(cls, line: str) -> 'Event':
    origin_str, time_str, details_str = line.strip().split(' | ')
    rank_str, _, node_str = origin_str.partition(':')
    kind_str = d.partition(' >>  ')[2] if '>>' in (d := details_str) else d
    kind = event_kind_registry[kind_str]
    date = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S,%f")
    rank = int(rank_str[4:]) if rank_str else 0
    node = int(node_str[3:]) if node_str else 0
    return cls(kind, date, rank, node)


class Stage2Job:
  def __init__(self, name: str, events: List[Event],
               start: datetime = None, end: datetime = None) -> None:
    self.name = name
    self.events = events
    self.start = start if start else min(e.date for e in events)
    self.end = end if end else max(e.date for e in events)

  @staticmethod
  def collect_events(err_path) -> List[Event]:
    """Collect `Event` instances from parsed lines of file at `err_path`"""
    events = []
    with open(err_path, 'r') as err_file:
      for line in err_file.readlines():
        try:
          events.append(Event.from_log_line(line))
        except (ValueError, KeyError):
          pass
    return events

  @staticmethod
  def collect_job_name(out_path: str, err_path: str) -> str:
    """Get stage2 job id from .out, .err, or first mainLog path"""
    if out_path:
      return Path(out_path).stem
    elif Path(err_path).suffix == '.err':
      return Path(err_path).stem
    else:  # if neither global .out nor .err are specified, use directory name
      return Path(err_path).parts[-2]

  @staticmethod
  def collect_paths(stage2_params) -> Tuple[Union[Path, None], List[Path]]:
    out_path = sorted(Path().glob(o))[0] if (o := stage2_params.out) else None
    err_paths_all = sorted(Path().glob(e if (e := stage2_params.err) else '*'))
    err_paths_valid = []
    for err_path in err_paths_all:
      try:
        err_file = open(err_path)
      except (FileNotFoundError, IsADirectoryError):
        pass
      else:
        err_paths_valid.append(err_path)
        err_file.close()
    if out_glob := stage2_params.out:
      out_path = sorted(Path().glob(out_glob))[0]
    elif len(err_paths_valid) == 1:
      err_path = err_paths_valid[0]
      if err_path.suffix == '.err' and err_path.with_suffix('.out').exists():
        out_path = err_path.with_suffix('.out')
    else:
      out_path = None
    return out_path, err_paths_valid

  @staticmethod
  def collect_start_end(out_path) -> Tuple[datetime, datetime]:
    """Collect date of "jobstart" and "jobend" from out file, if present"""
    try:
      with open(out_path, 'r') as out_file:
        lines = out_file.readlines()
        jobstart_line = [x for x in lines if 'jobstart' in x][0]
        jobend_line = [x for x in lines if 'jobstart' in x][0]
        fmt = ' %a %d %b %Y %I:%M:%S %p %Z\n'
        start_date = datetime.strptime(jobstart_line, 'jobstart' + fmt)
        end_date = datetime.strptime(jobend_line, 'jobend' + fmt)
      return start_date, end_date
    except (TypeError, IndexError):
      return None, None

  @classmethod
  def from_params(cls, stage2_params):
    out_path, err_paths = cls.collect_paths(stage2_params)
    start, end = cls.collect_start_end(out_path)
    name = cls.collect_job_name(out_path, err_paths[0])
    event_lists = [cls.collect_events(ep) for ep in err_paths]
    events = list(chain.from_iterable(event_lists))
    return cls(name, events, start, end)

  @property
  def ranks(self) -> List[int]:
    return sorted({event.rank for event in self.events})


def timedelta_in_minutes(start: datetime, end: datetime) -> float:
  return (start.timestamp() - end.timestamp()) / 60.


def plot_stage2_jobs_weather_plot(jobs: Iterable[Stage2Job]) -> None:
  fig, ax = plt.subplots(1, 1)
  for job_idx, job in enumerate(jobs):
    y_space = np.linspace(job_idx - .5, job_idx + .5, len(job.ranks) + 2)[1:-1]
    for rank, y in zip(job.ranks, y_space):
      for ek in event_kinds:
        xs = np.array([timedelta_in_minutes(e.date, job.start)
                       for e in job.events if e.kind is ek])
        ys = np.repeat(y, len(xs))
        ax.plot(xs, ys, color=ek.color, marker='o', linestyle=' ')
    x0s = np.repeat(0, len(y_space))
    x1s = np.repeat(timedelta_in_minutes(job.end, job.start), len(y_space))
    ax.plot(x0s, y_space, color='gray')
    ax.plot(x1s, y_space, color='gray')
  ax.set_title('diffBragg stage2 weather plot')
  ax.set_xlabel('Time since job start [min]')
  ax.set_ylabel('Slurm ID')
  ax.set_yticks(list(range(len(jobs))))
  ax.set_yticklabels([job.name for job in jobs])
  ax.legend(handles=[ek.handle for ek in event_kinds])
  plt.show()



def run(parameters) -> None:
  stage2_jobs = []
  for stage2_params in parameters.stage2:
    stage2_jobs.append(Stage2Job.from_params(stage2_params))
  plot_stage2_jobs_weather_plot(stage2_jobs)



params = []
if __name__ == '__main__':
  params, options = parse_phil(phil_scope_str)
  if '-h' in options or '--help' in options:
    print(__doc__)
    exit()
  run(params)