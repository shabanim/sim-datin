"""
Alignment handler is responsible to align tasks according to specific interrupt.

Task execution can be related to some events happen in the system, even if the resource is ready.
e.g. vsync tasks should occur only after Vsync interrupts.
"""

from collections import defaultdict, namedtuple
import pandas as pd

from asap.extensions import BaseRunTime
from asap.strings import S_2_US, ALIGNMENT_STATUS, RELEASED_FROM_ALIGNMENT, PENDING_ON_ALIGNMENT, WLTASK_NAME
from pnets.simulation import EVENTS

AlignmentEvent = namedtuple('AlignmentEvent', ('TASK', 'READY', 'RELEASED', 'ALIGNMENT_CLOCK', 'WAIT_DURATION'))
AlignmentTick = namedtuple('AlignmentTick', ('TIME', 'ALIGNMENT_CLOCK', ))


class AlignmentClock:
    """
    Alignment clock, interrupts can be related to specific frequency, means this interrupt will happen each # time.

    e.g. Vsync is type of interrupt that happens each frame.
        Say freq is 60MHz, means this interrupt happens each 16.6ms

    :param name: Alignment clock name, unique.
    :param _type: Alignment type
    :param device: Alignments related to specific device
    :param frequency: in HZ
    :param offset: offset from simulation start to starts the first alignment.
    """
    def __init__(self, name, _type, device, frequency, offset):
        self._name = name
        self._type = _type
        self._device = device
        self._frequency = frequency
        self._offset = offset
        self._wait_delay = (1.0/frequency) * S_2_US

    @property
    def name(self):
        return self._name

    @property
    def wait_delay(self):
        return self._wait_delay

    @property
    def frequency(self):
        return self._frequency

    @property
    def offset(self):
        return self._offset


class AlignmentHandler(BaseRunTime):
    """
    Alignment handler class. Holds queue of tasks waiting to specific interrupt to happen according to clock alignment.

    Holds:
        * alignments: dict of Alignment name in UPPER_CASE to proper AlignmentClock
        * tasks_queues: tasks ready to be executed but waiting for alignment. Dictionary of alignment -> tasks queue
    """
    def __init__(self, sim, system_mgr):
        super().__init__(sim, system_mgr)
        self._alignments = dict()
        self._tasks_queues = defaultdict(list)
        self._generate_alignments()
        self._sim.connect_to_event(EVENTS.TASK_READY, self._task_got_ready)
        self._alignments_data = list()
        self._alignments_ticks = list()

    def _task_got_ready(self, transition):
        task = self._get_task(transition)
        if task is None:
            return

        align_clock = task.get_attribute('align_to_clock', None)
        if align_clock is None:
            return

        self._tasks_queues[align_clock].append(task)
        task.attach_attribute(ALIGNMENT_STATUS, PENDING_ON_ALIGNMENT)
        task.attach_attribute('START_PENDING', self._sim.now)

    def _generate_alignments(self):
        clocks = self._system_mgr.workload.attributes.get('clocks', list())
        for clock in clocks:
            alignment_name = clock.get('name')
            self._alignments[alignment_name] = AlignmentClock(clock.get('name'), clock.get('type'), clock.get('device'),
                                                              clock.get('frequency'), clock.get('offset'))
            self._sim.insert_event(alignment_name, self._sim.now + clock.get('offset'),
                                   lambda: self._release_task(alignment_name))

    def _release_task(self, alignment_name):
        self._alignments_ticks.append(AlignmentTick(TIME=self._sim.now, ALIGNMENT_CLOCK=alignment_name))
        alignment = self._alignments[alignment_name]
        self._sim.insert_event(alignment_name, self._sim.now + alignment.wait_delay,
                               lambda: self._release_task(alignment_name))
        alignment_tasks = self._tasks_queues[alignment_name]
        if len(alignment_tasks) > 0:
            task = alignment_tasks.pop(0)
            task.attach_attribute(ALIGNMENT_STATUS, RELEASED_FROM_ALIGNMENT)
            t_name = task.name if task.get_attribute(WLTASK_NAME, '') == '' else \
                task.get_attribute(WLTASK_NAME, '') + task.name
            self._alignments_data.append(AlignmentEvent(TASK=t_name,
                                                        READY=task.get_attribute('START_PENDING'),
                                                        RELEASED=self._sim.now,
                                                        ALIGNMENT_CLOCK=alignment_name,
                                                        WAIT_DURATION=(self._sim.now -
                                                                       task.get_attribute('START_PENDING'))))

    def get_alignments_data(self):
        return pd.DataFrame(self._alignments_data)

    def get_alignments_ticks(self):
        return pd.DataFrame(self._alignments_ticks)

    def create_ticks_graph(self):
        from bokeh.plotting import figure
        from bokeh.palettes import Category20
        from bokeh.models import HoverTool
        from itertools import cycle
        from bokeh.plotting.helpers import _get_range, _get_scale
        from bokeh.models import (CategoricalAxis, ColumnDataSource)
        from bokeh.transform import dodge
        import pandas

        alignment_ticks = self.get_alignments_ticks()
        if alignment_ticks.empty:
            return figure()

        ys = alignment_ticks.ALIGNMENT_CLOCK.unique()
        fig = figure(title='Time:', plot_width=1000, plot_height=300, tools=['xpan', 'xwheel_zoom'],
                     active_scroll='xwheel_zoom', y_range=ys)

        colors = {}
        palette = cycle(Category20[20])

        ticks = sorted(set(alignment_ticks['ALIGNMENT_CLOCK'].unique()))
        fig.y_range = _get_range(ticks)
        fig.y_scale = _get_scale(fig.y_range, 'auto')
        if len(fig.left) and not isinstance(fig.left[0], CategoricalAxis):
            fig.left[0] = CategoricalAxis()

        rectangles = []

        for start, alignment_clock in alignment_ticks[['TIME', 'ALIGNMENT_CLOCK']].itertuples(index=False):
            if alignment_clock in colors:
                color = colors[alignment_clock]
            else:
                color = next(palette)
                colors[alignment_clock] = color

            rectangles.append((start, start+0.0001, alignment_clock, color))

        rectangles = pandas.DataFrame(rectangles, columns=['left', 'right', 'lane', 'color'])
        src = ColumnDataSource.from_df(rectangles)
        quad = fig.quad(source=src, left='left', right='right', bottom=dodge('lane', -0.45, range=fig.y_range),
                        top=dodge('lane', +0.45, range=fig.y_range), color='color')
        hover = HoverTool(renderers=[quad], tooltips=[('time', '@left')])
        fig.add_tools(hover)
        return fig
