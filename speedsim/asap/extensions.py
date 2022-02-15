"""
**Extensions** - defines all SpeedSim base extensions
"""
from asap.hw import GlobalClock
from asap.strings import PENALTY, RESOURCE, TASK, TaskMetaData
from asap.workload import TYPES
from pnets.simulation import EVENTS


class BaseRunTime:
    """
    Base runtime extension defines tasks runtime.

        - Proc task: (task processing cycles) * (resource clock period)
        - Read/Write task: 0, since by default there is no fabric modeling

    Base runtime extension connects to simulation events:
        - TASK_EXECUTE: whenever task got executed it update its runtime accordingly

    :param sim: SpeedSim object
    :param system_mgr: SystemMgr object
    """
    def __init__(self, sim, system_mgr):
        self._sim = sim
        self._system_mgr = system_mgr
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self._on_task_execute)

    @staticmethod
    def _get_task(transition):
        """
        Getting Asap.Workload task object out of SpeedSim task

        :param transition:
        :return: Task
        """
        return transition.get_pnml_attribute(TASK)

    @staticmethod
    def _get_resource(resource):
        """
        Getting Asap.Platform resource out of SpeedSim resource

        :param resource:
        :return:
        """
        if resource is None or resource.resource_type == 'NULL':
            return None
        return resource.get_attribute(RESOURCE)

    @staticmethod
    def _update_unmapped_task(task):
        """
        Updating unmapped tasks runtime (processing cycles)* (GLobalClock period)

        :param task:
        :return:
        """
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task.processing_cycles * GlobalClock.instance.period)

    @staticmethod
    def _update_proc_task(task, resource):
        """
        Updating processing tasks runtime (processing cycles) * (resource clock period) * penalty

        :param task:
        :param resource:
        :return:
        """
        penalty = resource.ip.get_attribute(PENALTY, 1)
        runtime = task.processing_cycles * resource.clock.period * penalty
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, runtime)

    @staticmethod
    def _update_mem_task(task, resource):
        """
        Updating memory tasks, by default its 0, no fabric inside our model

        :param task:
        :param resource:
        :return:
        """
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, 0)

    def _handle_task(self, transition, task):
        """
        Handles the task by updating the SpeedSim Transition runtime according to task runtime attribute

        :param transition:
        :param task:
        :return:
        """
        transition.runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME, 0)

    def _on_task_execute(self, transition, resource):
        """
        Happens each time a task got executed. set task run time according to type

        :param transition: SpeedSim transition presents task
        :param resource: SpeedSim resource object presents resource scheduled for this task
        :return:
        """
        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            self._update_unmapped_task(task)
            return

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            self._update_proc_task(task, hw_resource)
        elif task.type == TYPES.READ or task.type == TYPES.WRITE:
            self._update_mem_task(task, hw_resource)

        self._handle_task(transition, task)
