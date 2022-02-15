import numpy

from pnets.attributes import DATA_BYTES, PROCESSING, TYPE
from pnets.simulation import EVENTS


class LoadExtension:
    """
    Custom extension samples simulation status each time task start.
        - if 1 task runs then tasks time does not change
        - if 2 tasks runs then tasks rest time multiplied by 1.5
        - if 3 tasks runs then tasks rest time multiplied by 2.5
        - if >3 tasks runs then tasks rest time multiplied by 3
        without going back
    Extension connect itself to TASK_EXECUTE event
    Scaling is done on previous scaling - incremental
    """
    scale_factors = [1, 1.5, 2.5, 3]

    def __init__(self, sim):
        self._sim = sim
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_tasks_executing)

    def on_tasks_executing(self, transition, resource):
        # NOTE: this implementation assumes that the event is emitted before transition.end_event is assigned
        #       so for the new transition it changes the runtime while for the other transitions it scales them.
        executed_tasks_len = len(self._sim.get_executing_tasks())
        total_scaling = numpy.prod(self.scale_factors[:executed_tasks_len])
        transition.runtime = total_scaling * transition.transition.get_attribute('runtime')

        end_events = []
        for executed_task in self._sim.get_executing_tasks():
            event = executed_task[0].end_event
            if event is not None and event.name == EVENTS.TASK_END:
                remaining_time = event.clock - self._sim.now
                diff = ((remaining_time * self.scale_factors[executed_tasks_len-1]) - remaining_time)
                event.clock += diff
                end_events.append(event)

        # Update events according to new times
        for event in end_events:
            self._sim.update_event(event)


class ComplexLoadExtension(LoadExtension):
    """
    Custom extension samples simulation status each time task start/finish.
        - if 1 task runs then tasks time does not change
        - if 2 tasks runs then tasks rest time multiplied by 1.5
        - if 3 tasks runs then tasks rest time multiplied by 2.5
        - if >3 tasks runs then tasks rest time multiplied by 3
        without going back
    Extension connect itself to TASK_EXECUTE and TASK_END event
    Scaling is done on previous scaling - incremental
    Taking into account when tasks finish
    """

    def __init__(self, sim):
        super().__init__(sim)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)

    def on_task_finish(self, trans, resource):
        executed_tasks_len = len(self._sim.get_executing_tasks())
        previous_scaling = numpy.prod(self.scale_factors[:(executed_tasks_len+1)])
        total_scaling = numpy.prod(self.scale_factors[:executed_tasks_len])

        end_events = []
        for executed_task in self._sim.get_executing_tasks():
            event = executed_task[0].end_event
            if event is not None and event.name == EVENTS.TASK_END:
                remaining_time = event.clock - self._sim.now
                if remaining_time == 0:
                    continue
                diff = ((remaining_time * (total_scaling/previous_scaling)) - remaining_time)
                event.clock += diff
                end_events.append(event)

        # Update events according to new times
        for event in end_events:
            self._sim.update_event(event)


class SimpleFabricExtension:
    """
    Custom extension samples simulation status each time task start/finish.
    System bw is decreased/increased according to amount of read/write tasks run in parallel
        - current bw = optimal_bw / len(executed_tasks)
    Extension connect itself to TASK_EXECUTE and TASK_END event
    """
    BW = "BW"

    def __init__(self, sim, optimal_bw):
        """
        :param sim:
        :param optimal_bw: bytes/us
        """
        self._sim = sim
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_tasks_execute)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)
        self._rw_executed_tasks_len = 0
        self._system_bw = self._optimal_bw = optimal_bw

    def _update_end_events(self, executed_tasks, bw, trans):
        end_events = []
        for executed_task in executed_tasks:
            if executed_task[0] == trans:
                continue
            event = executed_task[0].end_event
            if event is not None and event.name == EVENTS.TASK_END:
                executed_task[0].attach_attribute(self.BW, bw)
                remaining_time = event.clock - self._sim.now
                diff = ((remaining_time * (self._system_bw / bw)) - remaining_time)
                event.clock += diff
                end_events.append(event)

        self._system_bw = bw

        # Update events according to new times
        for event in end_events:
            self._sim.update_event(event)

    def on_tasks_execute(self, transition, resource):
        if transition.get_pnml_attribute(TYPE) == PROCESSING:
            return

        read_write_tasks = [t for t in self._sim.get_executing_tasks() if t[0].get_pnml_attribute(TYPE) != PROCESSING]
        self._rw_executed_tasks_len = len(read_write_tasks)
        bw = self._optimal_bw/self._rw_executed_tasks_len
        transition.runtime = transition.get_pnml_attribute(DATA_BYTES)/bw
        self._update_end_events(read_write_tasks, bw, None)

    def on_task_finish(self, trans, resource):
        if trans.get_pnml_attribute(TYPE) == PROCESSING:
            return

        read_write_tasks = [t for t in self._sim.get_executing_tasks() if t[0].get_pnml_attribute(TYPE) != PROCESSING]
        self._rw_executed_tasks_len = len(read_write_tasks) - 1

        if self._rw_executed_tasks_len == 0:
            self._system_bw = self._optimal_bw
            return

        bw = self._optimal_bw/self._rw_executed_tasks_len
        self._update_end_events(read_write_tasks, bw, trans)
