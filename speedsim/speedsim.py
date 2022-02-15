#!/p/dpg/arch/perfhome/python/miniconda37/bin/python
"""
SpeedSim wrapper. Knows both, pnets and architecture. knows how to connect SpeedSim simulator to Architecture design.
"""

from pandas import concat

from asap.buses import Bus
from asap.extensions import BaseRunTime
from asap.mapping import Mapping
from asap.strings import (END_TRIGGER, NAME_SEPARATOR, RESOURCE, START_TRIGGER,
                          TASK, TRIGGER_IN, TRIGGER_OUT, ResourceDesc,
                          SchedulingState, TaskMetaData)
from asap.system_mgr import SystemMgr
from asap.system_platform import Platform
from asap.workload import Workload
from pnets.simulation import EVENTS, ResourceState, Simulator
from post_processing.utils import HW_EVENT, NAN, AnalysisData
from speedsim_utils import (prepare_hw_resources, prepare_wl_to_sim,
                            report_usage)


class AnalysisExtension:
    """
    Tracks and saves analysis information during the simulation
    """
    ANALYSIS_EVENT = 'ANALYSIS_EVENT'
    DONT_UPDATE = 'DONT_UPDATE'

    def __init__(self, sim):
        self._sim = sim
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_task_execute)
        self._sim.connect_to_event(self.ANALYSIS_EVENT, self._fill_hw_events)

    def on_task_execute(self, transition, resource):
        task = transition.get_pnml_attribute(TASK)
        if task is None:
            transition_name = transition.transition.id
            if transition_name.endswith('START/start_trigger'):
                AnalysisData.add_net(transition_name)
            return
        if task.get_attribute(self.DONT_UPDATE, False):
            return
        r = resource.get_attribute(RESOURCE)
        if r is None:
            return
        self._fill_hw_events(r, task, True)

    def on_task_finish(self, transition, resource):
        task = transition.get_pnml_attribute(TASK)
        if task is None:
            return
        if task.get_attribute(self.DONT_UPDATE, False):
            return
        r = resource.get_attribute(RESOURCE)
        if r is None:
            return
        self._fill_hw_events(r, task, False)

    def _fill_hw_events(self, resource, task, start=True):
        AnalysisData.add_ip_event(HW_EVENT(RESOURCE=resource.ip.name + NAME_SEPARATOR + resource.name,
                                           START=self._sim.now if start else NAN,
                                           FINISH=self._sim.now if not start else NAN))

        memories = task.get_attribute(TaskMetaData.TASK_MEMORIES)
        if memories is not None:
            for memory in memories:
                if memory is not None:
                    AnalysisData.add_memory_event(HW_EVENT(RESOURCE=memory.name, START=self._sim.now if start else NAN,
                                                           FINISH=self._sim.now if not start else NAN))

        paths = task.get_attribute(TaskMetaData.TASK_ROUTING_PATH)
        if paths is not None:
            for path in paths:
                if path is not None:
                    for bus in path:
                        if isinstance(bus, tuple) and bus[1] == ResourceDesc.BUS:
                            AnalysisData.add_bus_event(HW_EVENT(RESOURCE=bus[0], START=self._sim.now if start else NAN,
                                                                FINISH=self._sim.now if not start else NAN))
                        elif isinstance(bus, Bus):
                            AnalysisData.add_bus_event(HW_EVENT(RESOURCE=bus.name,
                                                                START=self._sim.now if start else NAN,
                                                                FINISH=self._sim.now if not start else NAN))


class SpeedSimScheduler:
    """
    Simulator scheduler.

    Behaves as a bridge scheduler between ASAP and simulator. Aware of both sides.
    """
    def __init__(self, sim, system_mgr: SystemMgr, hw_resources, connect=True):
        self._sim = sim
        self._system_mgr = system_mgr
        self._hw_resources = hw_resources
        if connect:
            self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)

    def schedule_transition(self, transition):
        """
        Scheduling transition (SpeedSim task).

        :param transition:
        :return:
        """
        task = self._get_task(transition)

        if task is None:
            return self._handle_none_task()

        resource, scheduling_state = self._schedule_task(task)
        return self._handle_task(transition, task, resource, scheduling_state)

    def _get_task(self, transition):
        """
        Getting task of speedSim transition

        :param transition:
        :return: Task
        """
        return transition.get_pnml_attribute(TASK)

    def _handle_none_task(self):
        """
        None tasks are speedsim helper tasks, that are not part of real workload, but still need to be handled.
        E.g. sync tasks, trigger tasks...
        NULL Resource handles None task - infinite resources.

        :return: NULL Resource
        """
        return ResourceState('NULL', 0)

    def _schedule_task(self, task):
        """
        Scheduling task

        :param task:
        :return: Resource, SchedulingState
        """
        return self._system_mgr.schedule_task(task)

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
        return resource_state

    def on_task_finish(self, transition, resource):
        task = transition.get_pnml_attribute(TASK)
        if task is None:
            return
        self._system_mgr.on_task_finish(task)


class SimScheduler(SpeedSimScheduler):
    """
    Example of extending basic scheduler.
    """
    def __init__(self, sim, system_mgr: SystemMgr, hw_resources):
        super().__init__(sim, system_mgr, hw_resources)

    def schedule_transition(self, transition):
        # modify only here
        resource_state = super().schedule_transition(transition)
        return resource_state


class SpeedSim:
    """
    Main application class.

    Receive all system components.
        - Platform
        - Workload
        - Mapping

    If Platform and mapping is not given then workload will run unmapped.
    SpeedSim is the main model so using it user can set own schedulers within the 3 scheduling levels
    or add as many extensions and he want.
    """
    def __init__(self, sys_platform: Platform, workload: Workload, mapping: Mapping, sim_scheduler=None):
        _mapping = mapping or Mapping('dummy_mapping', workload)
        _sys_platform = sys_platform or Platform('dummy_platform')

        self._sys_mgr = SystemMgr(_sys_platform, workload, _mapping)
        self._hw_resources = prepare_hw_resources(_sys_platform)
        self._workload_pnml_model = prepare_wl_to_sim(workload, _mapping)

        self._sim = Simulator(self._workload_pnml_model, dict())
        self._sim.set_resources(self._hw_resources.values())

        self.sim_scheduler = sim_scheduler or SimScheduler(self._sim, self._sys_mgr, self._hw_resources)
        self._sim.scheduler = self.sim_scheduler

        self._analysis_extension = None
        self._extensions = dict()
        self.add_extension('BaseRunTimeExtension', BaseRunTime)

    def set_system_scheduler(self, system_scheduler=None, properties=None):
        """
        Setting System level scheduler
        :param system_scheduler: System Scheduler class
        :param properties: scheduler properties
        :return:
        """
        if system_scheduler is None:
            return
        self._sys_mgr.scheduler = system_scheduler(self._sys_mgr, properties)

    def set_platform_scheduler(self, platform_scheduler=None):
        """
        Setting System level scheduler
        :param platform_scheduler: Platform Scheduler class
        :return:
        """
        if platform_scheduler is None:
            return
        self._sys_mgr.scheduler.set_platform_scheduler(platform_scheduler(self._sys_mgr))

    def set_sim_scheduler(self, sim_scheduler):
        """
        Setting speedSim level scheduler
        :param sim_scheduler: SpeedSim Scheduler class
        :return:
        """
        self.sim_scheduler = sim_scheduler(self._sim, self._sys_mgr, self._hw_resources)
        self._sim.scheduler = self.sim_scheduler

    def add_extension(self, extension_name, extension):
        """
        Appending new extension to sim
        :param extension_name:
        :param extension: object
        :return:
        """
        self._extensions[extension_name] = extension(self._sim, self._sys_mgr)
        return self._extensions[extension_name]

    def get_resource(self, resource):
        name = resource.ip.name + NAME_SEPARATOR + resource.name
        return self._hw_resources.get(name, None)

    def simulate(self, duration=1000000):
        """
        Simulate
        :param duration:
        :return:
        """
        self._sys_mgr.sys_platform.reset()
        self._analysis_extension = AnalysisExtension(self._sim)
        AnalysisData.reset()
        res = self._sim.run(duration)
        to_del = res[res['TRANSITION'].str.endswith(TRIGGER_IN) | res['TRANSITION'].str.endswith(TRIGGER_OUT) |
                     res['TRANSITION'].str.endswith(START_TRIGGER) | res['TRANSITION'].str.endswith(END_TRIGGER)]
        AnalysisData.instance.task_table = concat([res, to_del]).drop_duplicates(keep=False).reset_index(drop=True)
        AnalysisData.instance.simulation_time = self._sim.now
        report_usage()
        return AnalysisData.instance.task_table

    @staticmethod
    def get_sim_time():
        """
        Getting simulation time

        :return: sim time in us
        """
        return AnalysisData.instance.simulation_time

    def get_extension(self, name):
        return self._extensions.get(name)

    def get_extended_task_table(self):
        from copy import deepcopy
        from pnets.attributes import CYCLES, RUNTIME
        task_table = deepcopy(AnalysisData.instance.task_table)
        pnml_runtime_list = list()
        pnml_cycle_list = list()
        for tr_name in list(task_table['TRANSITION']):
            transition = self._workload_pnml_model.nets[0].get_transition(tr_name)
            task = transition.get_attribute(TASK)
            if task is None:

                pnml_runtime_list.append(0)
                pnml_cycle_list.append(0)
            else:
                pnml_runtime_list.append(task.get_attribute(RUNTIME, 0))
                pnml_cycle_list.append(task.get_attribute(CYCLES, 0))

        task_table['PNML_RUNTIME'] = pnml_runtime_list
        task_table['PNML_CYCLES'] = pnml_cycle_list
        return task_table

    @staticmethod
    def get_activated_workload_num():
        """
        :return: Number of simunlated nets
        """
        return len(set(AnalysisData.instance.start_triggers))
