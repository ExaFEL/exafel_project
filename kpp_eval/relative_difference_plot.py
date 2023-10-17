from enum import Enum
from typing import Dict, List, NamedTuple, Tuple

from matplotlib.legend_handler import HandlerTuple
from matplotlib import pyplot as plt
from matplotlib import colormaps

floats = List[float]


class Sample(Enum):
    cry11Ba = 0
    cytochrome = 1
    thermolysin = 2
    yb_lyso = 3


class JobStep(NamedTuple):
    sample: Sample
    step: int


def main() -> None:
    results: Dict[JobStep, Tuple[float, float, floats, floats]] = {
        JobStep(Sample.cry11Ba, 0): (0.0674, 0.0648, [], []),
        JobStep(Sample.cry11Ba, 1): (0.0681, 0.0611, [], []),
        JobStep(Sample.cry11Ba, 2): (0.0677, 0.0773, [], []),
        JobStep(Sample.cry11Ba, 3): (0.0772, 0.1070, [], []),
        JobStep(Sample.cry11Ba, 4): (0.1441, 0.2640, [], []),
        JobStep(Sample.cytochrome, 0): (0.0332, 0.0447, [204.27], [200.22]),
        JobStep(Sample.cytochrome, 1): (0.0331, 0.0456, [199.28], [184.89]),
        JobStep(Sample.cytochrome, 2): (0.0386, 0.0479, [166.99], [149.71]),
        JobStep(Sample.cytochrome, 3): (0.0504, 0.0600, [107.10], [ 75.13]),
        JobStep(Sample.cytochrome, 4): (0.0748, 0.0975, [ 63.77], [ 25.28]),
        JobStep(Sample.thermolysin, 0): (0.0438, 0.0471, [28.60, 75.09, 59.95, 59.68, 68.11], [29.46, 78.89, 62.64, 62.44, 71.42]),
        JobStep(Sample.thermolysin, 1): (0.0450, 0.0435, [28.01, 73.72, 58.67, 58.59, 66.38], [28.73, 76.82, 61.17, 60.69, 69.09]),
        JobStep(Sample.thermolysin, 2): (0.0471, 0.0428, [25.73, 69.41, 54.93, 55.06, 62.45], [26.11, 70.65, 55.71, 56.02, 63.52]),
        JobStep(Sample.thermolysin, 3): (0.0535, 0.0383, [21.71, 56.00, 43.90, 45.58, 50.25], [21.16, 54.83, 42.11, 44.04, 49.03]),
        JobStep(Sample.thermolysin, 4): (0.0636, 0.0529, [13.83, 38.74, 30.53, 32.12, 35.09], [13.51, 37.48, 28.32, 30.39, 33.75]),
        JobStep(Sample.yb_lyso, 0): (0.0635, 0.0762, [52.81, 32.33], [48.29, 30.36]),
        JobStep(Sample.yb_lyso, 1): (0.0764, 0.0972, [48.74, 29.29], [32.75, 20.54]),
        JobStep(Sample.yb_lyso, 2): (0.1004, 0.1200, [40.52, 24.70], [34.99, 21.66]),
        JobStep(Sample.yb_lyso, 3): (0.1316, 0.1891, [30.42, 19.41], [ 7.96,  7.01]),
        JobStep(Sample.yb_lyso, 4): (0.1627, 0.1973, [21.33, 13.78], [14.50,  8.61]),
    }

    colors = colormaps['tab10']
    markers = 'o^sv'

    def plot_diff(title: str, o: int = 0) -> None:
        fig, ax = plt.subplots()
        handles = []
        for job_step, result in results.items():
            c = colors(job_step.sample.value)
            m = markers[job_step.sample.value]
            l_ = job_step.sample.name
            h, = ax.loglog(result[0+o], result[1+o], c=c, marker=m,
                           ms=(5-job_step.step)+5, linestyle="None",
                           label='' if job_step.step else l_)
            handles.append(h)
        ax.legend([tuple(handles[:5]), tuple(handles[5:10]),
                   tuple(handles[10:15]), tuple(handles[15:])],
                  [s.name for s in Sample],
                  handler_map={tuple: HandlerTuple(ndivide=None)},
                  handlelength=7.5)
        lims = min(l := [*ax.get_xlim(), *ax.get_ylim()]), max(l)
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_title(title)
        ax.set_xlabel('DIALS')
        ax.set_ylabel('diffBragg')
        ax.axline((0, 0), (1, 1), color='k')
        plt.subplots_adjust(left=0.15, right=0.95)
        plt.show()

    plot_diff('Disagreement with ground truth', o=0)
    plot_diff('Anomalous signal strength', o=2)


if __name__ == '__main__':
    main()