"""
**Mapping** file - definition of mapping and its components.
"""
from collections import defaultdict

from .workload import Task, Workload


class MappingEntity:
    """
    Simple mapping entity defines task mapping to any hw resources.
    """
    def __init__(self, task: Task, resource, **kwargs):
        self._task = task
        self._resource = resource
        self._attributes = dict()
        for attribute, val in kwargs.items():
            self._attributes[attribute] = val

    @property
    def task(self):
        """
        :return: Task
        """
        return self._task

    @property
    def resource(self):
        """
        :return: Resource
        """
        return self._resource

    def attach_attribute(self, attribute, value):
        self._attributes[attribute] = value

    def get_attribute(self, attribute):
        self._attributes.get(attribute, None)


class Mapping:
    """
    Mapping defines workloads tasks to mappings.

    Each task may have multiple mappings.
    """
    def __init__(self, name, workload: Workload):
        self._name = name
        self._workload = workload
        self._mappings = defaultdict(list)

    @property
    def name(self):
        """
        :return: Mapping name
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Setting mapping name

        :param name:
        :return:
        """
        self._name = name

    @property
    def mappings(self):
        """
        :return: Mappings list - each is MappingEntity
        """
        return self._mappings

    def map_task(self, task: Task, resource, **kwargs):
        """
        Map task to this specific resource

        :param task:
        :param resource:
        :param kwargs:
        :return:
        """
        self._mappings[task.name].append(MappingEntity(task, resource, **kwargs))

    def get_task_mapping(self, task_name):
        """
        :param task_name:
        :return: List of task mappings
        """
        return self._mappings[task_name]

    def add_mapping_entity(self, mapping_entity: MappingEntity):
        """
        Adds mapping entity to the mappings attribute

        :param mapping_entity:
        """
        self._mappings[mapping_entity.task.name].append(mapping_entity)
