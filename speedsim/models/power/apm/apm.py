"""
APM - Abstract Power Manager - manages power related behavior.
APM is an extension connects SpeedSim to Power Manager defined in Nemo.
While exposing frequency update function to be overwritten.
"""

import os
import sys
import tempfile
from collections import Counter, defaultdict, namedtuple

import pandas

from asap.strings import (ALL_ELEMENTS, AND, NAME_SEPARATOR, OR, PENALTY,
                          RESOURCE, TYPE, SchedulingState, StateDesc,
                          TaskMetaData)
from asap.workload import TYPES
from pnets.simulation import EVENTS, ResourceState
from post_processing.tables import (LogicExpression,
                                    convert_expression_to_dict,
                                    convert_string_expression_to_dict,
                                    get_concurrency_table)
from post_processing.utils import (convert_heartbeat_to_interval_table,
                                   get_residency_table)
from speedsim import SpeedSimScheduler
from speedsim_utils import Logger
from strings import NEMO_PATH, SC_PACKAGE

sc_package = os.environ[SC_PACKAGE]
if sc_package not in sys.path:
    sys.path.append(sc_package)

nemo_path = os.environ[NEMO_PATH]
if nemo_path not in sys.path:
    sys.path.append(nemo_path)

from apm_lib import ApmProxy, ResidencyCalculator, StateChangeListener  # isort:skip # noqa: E402
from sc import SC_US, sc_start, sc_time, sc_time_stamp  # isort:skip # noqa: E402

frequency_event = namedtuple('FrequencyEvent', ('TIME', 'RESOURCE', 'CLOCK', 'FREQUENCY'))
state_event = namedtuple('StateEvent', ('TIME', 'RESOURCE', 'STATE'))
transitions_event = namedtuple('TransitionEvent', ('TIME', 'RESOURCE', 'FROM_STATE', 'TO_STATE', 'DIRECTION'))


class SpeedSimListener(StateChangeListener):
    """
    SpeedSim Listener listens to changes and behave accordingly.
    Inherits from Nemo base listener.
    """
    def __init__(self, *args, **kwargs):
        StateChangeListener.__init__(self, *args, **kwargs)
        self.sim = None
        self.apm = None
        self.frequency_data = list()
        self.states_data = list()
        self.system_states_data = list()
        self.transitions_data = list()

    @staticmethod
    def get_time():
        return sc_time_stamp().to_seconds() * 1e6

    def direct_update_state(self, module, state):
        """
        Updating state of module.
        :param module:
        :param state:
        :return:
        """
        # print('Updating state of module: ', module, ' in time: ', self.get_time(), ' to:', state)
        if state == StateDesc.DEFAULT:
            return False

        if state.startswith('power_up') or state.startswith('power_down'):
            direction, trans = state.split('_from_')
            from_state, to_state = trans.split('_to_')
            r = self.apm.resources.get(module)
            if r is None:
                self.transitions_data.append(
                    transitions_event(TIME=self.sim.now, RESOURCE=module, FROM_STATE=from_state,
                                      TO_STATE=to_state, DIRECTION=direction))
            else:
                self.transitions_data.append(
                    transitions_event(TIME=self.sim.now, RESOURCE=r.resource_type, FROM_STATE=from_state,
                                      TO_STATE=to_state, DIRECTION=direction))
            return False
        r = self.apm.resources.get(module)
        if r is None:
            self.system_states_data.append(state_event(TIME=self.sim.now, RESOURCE=module, STATE=state))
            return False
        self.states_data.append(state_event(TIME=self.sim.now, RESOURCE=r.resource_type, STATE=state))
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

        # Gathering relevant resources, all resources connected to the same clock
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
        # print('Updating Voltage of module: ', module, ' in time: ', self.get_time(), ' to:', voltage)
        return False

    def direct_update_temperature(self, module, temperature):
        # print('Updating Temperature of module: ', module, ' in time: ', self.get_time(), ' to:', temperature)
        return False

    def enable_sched(self, module):
        # print('Enabling sched of module: ', module, ' in time: ', self.get_time())
        self.apm.update_tasks_on_module(module)
        return False

    def disable_sched(self, module):
        # print('Disable sched of module: ', module, ' in time: ', self.get_time())
        return False


class APM(SpeedSimScheduler):
    """
        Manage connection between SpeedSim and power management unit.
    """
    HEART_BEAT_EVENT = "HEART_BEAT_EVENT"
    HEART_BEAT = 0.1
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
        self._heart_beat = self.HEART_BEAT

        self._pending_tasks_on_sleep_resource = defaultdict(list)
        self._pending_tasks_on_awake_resource = defaultdict(list)

        self.turn_on_requests = list()
        self.resource_turn_on_requests = Counter()

    def instantiate(self, updater, listener, heart_beat=10.0):
        self._listener = listener
        self._listener.sim = self._sim
        self._listener.apm = self

        self._updater = updater
        self._rc = ResidencyCalculator()

        tmp_path = tempfile.mkdtemp()
        self._system_mgr.sys_platform.dump_power_connectivity_file(tmp_path)
        power_file_path = tmp_path + '/' + self._system_mgr.sys_platform.name + '_power_states.csv'
        connectivity_file_path = tmp_path + '/' + self._system_mgr.sys_platform.name + '_connectivity.csv'
        self._apm = ApmProxy('sim', 1000, self._updater, self._rc, listener, power_file_path, connectivity_file_path)
        self._heart_beat = heart_beat

        self.resources = dict()
        for r in self._sim.get_resources():
            self.resources[self.get_name(r)] = r
            self._apm.add_module(self.get_name(r))
            self._apm.register_state_change(self._listener, self.get_name(r))

        sc_start(sc_time(1, SC_US))
        self._sim.insert_event(self.HEART_BEAT_EVENT, self._sim.now + self.HEART_BEAT, lambda: self.heart_beat())

    def heart_beat(self):
        sc_start(sc_time(self._heart_beat, SC_US))
        # if not self._sim.get_events() and not self._sim.get_ready_tasks() and self._sim.now > 0:
        #     print('No more events - finished heart beat at ', self._sim.now)
        #     return
        self._sim.insert_event(self.HEART_BEAT_EVENT, self._sim.now + self._heart_beat, lambda: self.heart_beat())

    def schedule_transition(self, transition):
        task = self._get_task(transition)
        if task is None:
            return self._handle_none_task()

        if self._is_zero_duration_task(task):
            return self._handle_zero_task(transition)

        if self._is_task_pending(task):
            return None

        resource = None
        scheduling_state = SchedulingState.NAN
        for res, tasks in self._pending_tasks_on_awake_resource.items():
            if task in tasks:
                resource = res
                scheduling_state = SchedulingState.SCHEDULED
                tasks.remove(task)
                break

        if resource is None:
            resource, scheduling_state = self._system_mgr.schedule_task(task)

        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task.processing_cycles *
                              self._system_mgr.sys_platform.global_clock.period)

        return self._handle_task(transition, task, resource, scheduling_state)

    def _handle_task(self, transition, task, resource, scheduling_state):
        """
        Handling task that is mapped to given resource. update speedsim accordingly.
        None resource is due to unmapped tasks or no available resource found. scheduling state defines the reason.
        :param transition: speedsim task
        :param task: workload task
        :param resource:
        :param scheduling_state: Scheduling task status, NAN, NULL, SCHEDULER...
        :return:
        """
        transition.runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME)

        if resource is None:
            if scheduling_state == SchedulingState.NULL:
                return ResourceState('NULL', 0)
            else:
                return None

        resource_state = self._hw_resources.get(resource.ip.name + NAME_SEPARATOR + resource.name, None)
        if resource_state is None:
            raise ValueError("Did not find resource " + resource.name + " in the platform")

        if not self.is_module_active(self.get_name(resource_state)):
            self._pending_task_on_resource(task, resource)
            self._apm.request_to_run(self.get_name(resource_state))
            return None

        penalty = 1 if resource.ip.get_attribute(PENALTY) is None else resource.ip.get_attribute(PENALTY)
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task.processing_cycles * resource.clock.period * penalty)
        transition.runtime = task.processing_cycles * resource.clock.period * penalty
        return resource_state

    def _handle_zero_task(self, transition):
        """
        Handles a zero transition, sets it runtime as 0 and maps it to NULL
        :param transition:
        :return:
        """
        transition.runtime = 0
        return ResourceState('NULL', 0)

    def _is_zero_duration_task(self, task):
        """
        Checks if the task runtime is lower than threshold
        :param task:
        :return:
        """
        return (task.type == TYPES.READ and task.read_bytes == 0) or \
               (task.type == TYPES.WRITE and task.write_bytes == 0) or \
               ((task.type == TYPES.PROC or task.type == TYPES.GEN) and task.processing_cycles == 0)

    def update_tasks_on_module(self, module):
        r = self.resources.get(module)
        if r is None:
            return
        resource = r.get_attribute(RESOURCE)
        if not self._pending_tasks_on_sleep_resource[resource]:
            return
        task = self._pending_tasks_on_sleep_resource[resource].pop(0)
        self._pending_tasks_on_awake_resource[resource].append(task)

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
        if self.resource_turn_on_requests[r] == 0:
            Logger.log(self._sim.now, 'Invoking workload for: ' + self.get_name(resource))
            self.resource_turn_on_requests[r] += 1
            self._apm.invoke_workload(True, self.get_name(resource))
            self._turn_on_buses_and_memories(transition, resource)

    def _turn_on_buses_and_memories(self, transition, resource):
        ftask = self._get_task(transition)
        if ftask.type == TYPES.PROC or ftask.type == TYPES.GEN:
            return

        r = resource.get_attribute(RESOURCE)
        if r is None:
            return

        all_elements = r.ip.get_attribute(ALL_ELEMENTS)
        if all_elements is None:
            all_elements = set()
            for mem in self._system_mgr.sys_platform.memories:
                for path in self._system_mgr.sys_platform.get_all_paths(r.ip, mem):
                    for elem in path[1:]:
                        all_elements.add(elem[0])
                        if elem[0] in self.turn_on_requests:
                            continue
                        self.turn_on_requests.append(elem[0])
                        Logger.log(self._sim.now, 'Invoking workload for: ' + elem[0])
                        self._apm.invoke_workload(True, elem[0])
            r.ip.attach_attribute(ALL_ELEMENTS, all_elements)
        else:
            for elem in all_elements:
                if elem in self.turn_on_requests:
                    continue
                self.turn_on_requests.append(elem)
                Logger.log(self._sim.now, 'Invoking workload for: ' + elem)
                self._apm.invoke_workload(True, elem)

    def on_task_finish(self, transition, resource):
        if resource.resource_type == 'NULL':
            return
        r = resource.get_attribute(RESOURCE)
        super().on_task_finish(transition, resource)
        Logger.log(self._sim.now, 'UN Invoking workload for: ' + self.get_name(resource))
        self.resource_turn_on_requests[r] -= 1
        if self.resource_turn_on_requests[r] == 0:
            self._apm.invoke_workload(False, self.get_name(resource))
            self._turn_off_buses_and_memories(transition, resource)

    def _turn_off_buses_and_memories(self, transition, resource):
        # TODO: Saeed boost performance
        ftask = self._get_task(transition)
        if ftask.type == TYPES.PROC or ftask.type == TYPES.GEN:
            return

        r = resource.get_attribute(RESOURCE)
        if r is None:
            return

        buses_memories = r.ip.get_attribute(ALL_ELEMENTS)

        read_write_tasks = [t for t in self._sim.get_executing_tasks() if
                            t[0].get_pnml_attribute(TYPE) != TYPES.PROC and t[0].get_pnml_attribute(TYPE) != TYPES.GEN]

        for executed_task in read_write_tasks:
            t = self._get_task(executed_task[0])
            if t is None:
                continue
            if t == ftask:
                continue

            r = executed_task[1].get_attribute(RESOURCE)
            if r is None:
                return

            for used_comp in r.ip.get_attribute(ALL_ELEMENTS):
                buses_memories.discard(used_comp)

        for non_used_comp in buses_memories:
            if non_used_comp in self.turn_on_requests:
                self.turn_on_requests.remove(non_used_comp)
            else:
                continue
            Logger.log(self._sim.now, 'UN Invoking workload for: ' + non_used_comp)
            self._apm.invoke_workload(False, non_used_comp)

    def resource_ready(self, resource):
        tasks = self._pending_tasks_on_sleep_resource[resource]
        self._pending_tasks_on_awake_resource[resource] = tasks
        del self._pending_tasks_on_sleep_resource[resource]

    def is_module_active(self, resource):
        return self._apm.is_module_active(resource)

    @staticmethod
    def get_name(r):
        return str(r.resource_type)

    def get_frequency_data(self):
        return pandas.DataFrame(self._listener.frequency_data)

    def get_states_data(self):
        return pandas.DataFrame(self._listener.states_data)

    def get_system_states_data(self):
        return pandas.DataFrame(self._listener.system_states_data)

    def get_transitions_data(self):
        return pandas.DataFrame(self._listener.transitions_data)

    def get_concurrency_states_by_expression(self, expression, start=0, end=None, intervals=1,
                                             expression_name='Expression'):
        """
        Returns concurrency table for system states with expression
        :param expression: {'OR'/'AND': [{hw:state}, {'OR'/'AND': [{...}]}]}
        :param start: start time of the window for residency table
        :param end: end time of the window for residency table
        :param intervals: amount of intervals for residency table
        :param expression_name: the expression name that will show in the outputted table
        :return: Runtime table, Residency table
        """
        from post_processing.setup import EXPRESSION
        runtime_states_table = \
            convert_heartbeat_to_interval_table(
                pandas.concat([self.get_system_states_data(), self.get_states_data()]), ['RESOURCE'], 'STATE')
        if isinstance(expression, str):
            expression = convert_string_expression_to_dict(expression)
        elif isinstance(expression, LogicExpression):
            expression = convert_expression_to_dict(expression)
        # Converts the expression to the format expression that the get concurrency table function knows
        expression = self.convert_states_expression(expression)
        runtime_states_table = get_concurrency_table(runtime_states_table, expression, expression_name=expression_name)
        runtime_states_table = runtime_states_table.rename(columns={EXPRESSION: 'RESOURCE'})
        res_states_table = get_residency_table(runtime_states_table, start, end, intervals)
        return runtime_states_table, res_states_table

    def convert_states_expression(self, states_expression):
        """
        Converts the states expression dict to the regular expressions that the function gets
        :return: Dict
        """
        regular_dict = dict()
        key = list(states_expression.keys())[0]
        if key != AND and key != OR:
            for key, value in states_expression.items():
                regular_dict['RESOURCE'] = key
                regular_dict['STATE'] = value
        else:
            regular_dict[key] = list()
            for condition in states_expression[key]:
                regular_dict[key].append(self.convert_states_expression(condition))

        return regular_dict
