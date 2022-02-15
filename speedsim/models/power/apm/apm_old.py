#!/p/dpg/arch/perfhome/python/miniconda3/bin/python3 -u
"""
APM - Abstract Power Manager - manages power related behavior.
APM is an extension connects SpeedSim to Power Manager defined in Nemo.
APM receives updater which update power related params (frequency/states/..) and SpeedSim
"""
import os
import sys
from strings import SC_PACKAGE, NEMO_PATH

sc_package = os.environ[SC_PACKAGE]
if sc_package not in sys.path:
    sys.path.append(sc_package)

nemo_path = os.environ[NEMO_PATH]
if nemo_path not in sys.path:
    sys.path.append(nemo_path)


from sc import SC_US, sc_start, sc_time, sc_time_stamp
from apm_lib import ResidencyCalculator, StateChangeListener, ApmProxy
from asap.strings import RESOURCE, TASK, SchedulingState, NAME_SEPARATOR, PENALTY
from collections import namedtuple
import pandas
from pnets.simulation import ResourceState

frequency_event = namedtuple('FrequencyEvent', ('TIME', 'RESOURCE', 'CLOCK', 'FREQUENCY'))


class SpeedSimListener(StateChangeListener):
    """
    SpeedSim Listener listens to changes and behave accordingly.
    """
    def __init__(self, *args, **kwargs):
        StateChangeListener.__init__(self, *args, **kwargs)
        self.sim = None
        self.apm = None
        self.frequency_data = list()

    @staticmethod
    def get_time():
        return sc_time_stamp().to_seconds() * 1e6

    def direct_update_state(self, module, state):
        print('Updating state of module: ', module, ' in time: ', self.get_time(), ' to:', state)
        return False

    def direct_update_frequency(self, module, frequency):
        """
        Updating frequency of module, change tasks runtime accordingly.
        :param module:
        :param frequency: in MHz
        :return:
        """
        # print('Updating frequency of module: ', module, ' in time: ', self.get_time(), ' to:', frequency)
        period = (1.0/frequency)  # in us
        r = self.apm.resources.get(module)
        if r is None:
            return
        resource = r.get_attribute(RESOURCE)
        self.frequency_data.append(frequency_event(TIME=self.sim.now, RESOURCE=r.resource_type,
                                                   CLOCK=resource.clock.name, FREQUENCY=frequency))
        rel_resources = list()
        for res in self.apm.resources.values():
            hw_res = res.get_attribute(RESOURCE)
            if hw_res is None:
                continue
            if resource.clock.name == hw_res.clock.name:
                rel_resources.append(res)

        end_events = []
        for executed_task in self.sim.get_executing_tasks():
            if executed_task[1] not in rel_resources:
                continue

            prev_period = resource.clock.period
            if period != 0 and prev_period != 0:
                scale = period/prev_period
            else:
                scale = 1
            event = executed_task[0].end_event
            if event is not None and event.name == EVENTS.TASK_END:
                remaining_time = event.clock - self.sim.now
                diff = ((remaining_time * scale) - remaining_time)
                event.clock += diff
                end_events.append(event)

        resource.clock.period = period

        for event in end_events:
            self.sim.update_event(event)
        return False

    def direct_update_voltage(self, module, voltage):
        print('Updating Voltage of module: ', module, ' in time: ', self.get_time(), ' to:', voltage)
        return False

    def direct_update_temperature(self, module, temperature):
        print('Updating Temperature of module: ', module, ' in time: ', self.get_time(), ' to:', temperature)
        return False


from speedsim import SpeedSimScheduler
from pnets.simulation import EVENTS
from collections import defaultdict
from asap.strings import SchedulingState
from .state_manager import StatesManager, CStatesBuilder


class APM(SpeedSimScheduler):
    """
        Manage connection between SpeedSim and power management unit.
    """
    HEART_BEAT_EVENT = "HEART_BEAT_EVENT"
    HEART_BEAT = 10
    INITIAL_FREQ = 2000
    WAKE_UP_EVENT = "WAKE_UP_EVENT"

    def __init__(self, sim, system_mgr, hw_resources):
        super().__init__(sim, system_mgr, hw_resources, False)
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_task_execute)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)
        self._updater = None
        self._rc = None
        self._apm = None
        self._listener = None
        self.resources = None
        self._states_mgr = StatesManager(self._sim, self, system_mgr.sys_platform, None)
        self._heart_beat = self.HEART_BEAT

        self._pending_tasks_on_sleep_resource = defaultdict(list)
        self._pending_tasks_on_awake_resource = defaultdict(list)

    def instantiate(self, updater, listener, heart_beat=10.0):
        self._listener = listener
        self._listener.sim = self._sim
        self._listener.apm = self

        self._updater = updater
        self._rc = ResidencyCalculator()
        self._apm = ApmProxy('sim', 1000, self._updater, self._rc)
        states_builder = CStatesBuilder(self._system_mgr.sys_platform)
        states_builder.instantiate_states()
        self._heart_beat = heart_beat

        self.resources = dict()
        for r in self._sim.get_resources():
            self.resources[self.get_name(r)] = r
            self._apm.add_module(self.get_name(r))
            self._apm.register_state_change(self._listener, self.get_name(r))
        self._states_mgr.update_resources(self.HEART_BEAT)
        self._sim.insert_event(self.HEART_BEAT_EVENT, self._sim.now + self.HEART_BEAT, lambda: self.heart_beat())

    def heart_beat(self):
        sc_start(sc_time(self._heart_beat, SC_US))
        if not self._sim.get_events() and not not self._sim.get_ready_tasks() and self._sim.now > 0:
            print('No more events - finished heart beat at ', self._sim.now)
            return
        self._states_mgr.update_resources(self._heart_beat)
        self._sim.insert_event(self.HEART_BEAT_EVENT, self._sim.now + self._heart_beat, lambda: self.heart_beat())

    def schedule_transition(self, transition):
        task = transition.get_pnml_attribute(TASK)
        if task is None:
            return ResourceState('NULL', 0)

        if task in sum(self._pending_tasks_on_sleep_resource.values(), []):
            return None

        resource = None
        scheduling_state = SchedulingState.NAN
        for res, tasks in self._pending_tasks_on_awake_resource.items():
            if task in tasks:
                resource = res
                scheduling_state = SchedulingState.SCHEDULED
                tasks.remove(task)
        if resource is None:
            resource, scheduling_state = self._system_mgr.schedule_task(task)
        if resource is None:
            transition.runtime = task.processing_cycles * self._system_mgr.sys_platform.global_clock.period
            if scheduling_state == SchedulingState.NULL:
                return ResourceState('NULL', 0)
            else:
                return None

        if not self._states_mgr.is_resource_awake(resource):
            self._states_mgr.pending_task_on_resource(resource)
            self._pending_tasks_on_sleep_resource[resource].append(task)
            return None
        resource_state = self._hw_resources.get(resource.ip.name + NAME_SEPARATOR + resource.name, None)
        if resource_state is None:
            raise ValueError("Did not find resource " + resource.name + " in the platform")

        penalty = 1 if resource.ip.get_attribute(PENALTY) is None else resource.ip.get_attribute(PENALTY)
        transition.runtime = task.processing_cycles * resource.clock.period * penalty
        return resource_state

    def _is_task_pending(self, task_name):
        return task_name in sum(self._pending_tasks_on_sleep_resource.values(), [])

    def _pending_task_on_resource(self, task, resource):
        self._pending_tasks_on_sleep_resource[resource].append(task)

    def on_task_execute(self, transition, resource):
        if resource.resource_type == 'NULL':
            return
        r = resource.get_attribute(RESOURCE)
        if r is None:
            return
        self._states_mgr.executing_resource(resource)
        self._apm.invoke_workload(True, self.get_name(resource))

    def on_task_finish(self, transition, resource):
        if resource.resource_type == 'NULL':
            return
        super().on_task_finish(transition, resource)
        self._apm.invoke_workload(False, self.get_name(resource))

    def resource_ready(self, resource):
        tasks = self._pending_tasks_on_sleep_resource[resource]
        self._pending_tasks_on_awake_resource[resource] = tasks
        del self._pending_tasks_on_sleep_resource[resource]

    @staticmethod
    def get_name(r):
        return str(r.resource_type) + "_" + str(r.index)

    def get_frequency_data(self):
        return pandas.DataFrame(self._listener.frequency_data)

    def get_cstates_data(self):
        return self._states_mgr.get_cstates_data()
