"""
SystemMgr file - holds the platform, workload and mapping.
"""
from .mapping import Mapping
from .schedulers import SystemScheduler
from .system_platform import Platform
from .workload import TYPES, Workload


class SystemMgr:
    """
    System manager, is aware of all system components. Platform, Workload and mapping.
    In addition, it has the system scheduler instance. and saves the system status, saves task executing resource
    """
    def __init__(self, sys_platform: Platform, workload: Workload, mapping: Mapping, scheduler=None):
        self._sys_platform = sys_platform
        self._workload = workload
        self._mapping = SystemMgr.get_hierarchy_mapping(workload, mapping)
        self._scheduler = scheduler or SystemScheduler(self)
        self._executing_tasks = dict()

    @property
    def sys_platform(self):
        """
        :return: system platform
        """
        return self._sys_platform

    @property
    def workload(self):
        """
        :return: Workload
        """
        return self._workload

    @property
    def mapping(self):
        """
        :return: Mapping
        """
        return self._mapping

    @property
    def scheduler(self):
        """
        :return: System scheduler
        """
        return self._scheduler

    @scheduler.setter
    def scheduler(self, scheduler):
        """
        Setting system scheduler
        :param scheduler:
        :return:
        """
        self._scheduler = scheduler

    def schedule_task(self, task, resource=None):
        """
        Schedule task on resource
        :param task:
        :param resource:
        :return:
        """
        return self._scheduler.schedule_task(task, resource)

    def on_task_finish(self, task):
        """
        On task finish function - call scheduler on task finish and removes task from executing_tasks list.
        :param task:
        :return:
        """
        self._scheduler.on_task_finish(task)
        if task in self._executing_tasks.keys():
            del self._executing_tasks[task]

    def on_task_execute(self, task, resource):
        self._executing_tasks[task] = resource

    def get_executing_task_resource(self, task):
        """
        Getting resource executes given task.
        :param task:
        :return: Resource
        """
        return self._executing_tasks.get(task, None)

    @staticmethod
    def get_hierarchy_mapping(workload: Workload, mapping: Mapping):
        """
        Merges the inner mappings of the workload tasks to the main mapping.
        :param workload:
        :param mapping:
        :return: Mapping
        """
        for task in workload.tasks:
            if task.type == TYPES.WORKLOAD:
                mapping_merge = SystemMgr.get_hierarchy_mapping(task.workload,
                                                                task.mapping)
                for mapping_entities in mapping_merge.mappings.values():
                    for mapping_entity in mapping_entities:
                        mapping.add_mapping_entity(mapping_entity)
        return mapping
