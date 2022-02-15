"""
**Scheduler** - define all basic schedulers only in this file
"""
from asap.hw import ComponentState, GlobalClock
from asap.mapping import MappingEntity
from asap.strings import (PENALTY, TASK_SPLIT_COUNT, WLTASK_NAME,
                          SchedulingState, TaskMetaData)
from asap.workload import TYPES


class Scheduler:
    """
    Naive scheduler - schedule task on given resource.
    """
    def __init__(self, properties=None):
        self._properties = properties if properties is not None else dict()

    def schedule_task(self, task, resource):
        """
        Naive scheduling task on resource. check if resource is free or busy.

        :param task:
        :param resource: should be driver/executing unit
                        or any other HW component has state and know how to execute task.
        :return: True if succeeded, False otherwise.
        """
        if resource.state == ComponentState.FREE:
            resource.state = ComponentState.BUSY
            resource.executing_task = task
            return resource
        return None

    def on_task_finish(self, resource):
        resource.executing_task = None
        resource.state = ComponentState.FREE

    def attach_attribute(self, attribute, value):
        self._properties[attribute] = value

    def get_attribute(self, attribute, default=None):
        self._properties.get(attribute, default)


class IPScheduler(Scheduler):
    """
    Naive IP-level scheduler

    Looks for free Accelerator for proc tasks and free Driver for read/write tasks.
    """
    def __init__(self, properties=None):
        super().__init__(properties)

    def schedule_task(self, task, resource):
        """
        Scheduling task to IP components. find the first free proper resource according to task type.

        :param task:
        :param resource: IP
        :return:
        """
        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            for ex_unit in resource.executing_units:
                if ex_unit.schedule_task(task) is not None:
                    resource.state = ComponentState.BUSY
                    return ex_unit
        elif task.type == TYPES.READ or task.type == TYPES.WRITE:
            for driver in resource.drivers:
                if driver.schedule_task(task) is not None:
                    resource.state = ComponentState.BUSY
                    return driver
        return None


class BaseSystemScheduler:
    """
    Platform level scheduler.

    Receive task, and mapping list.
    Scheduler try to schedule task according to the mapping, first mapping succeeds will be returned.
    Also it activates and deactivate all of the routing path from source to destination.
    """

    def __init__(self, system_mgr, properties=None):
        self._system_mgr = system_mgr
        self._properties = properties if properties is not None else dict()

    def schedule_task(self, task, mappings):
        """
        First level Scheduler
        Schedule task according to mappings.
        Scheduler receives the list of mappings relevant for the task, tries to map task ot one of it.
        Scheduler update buses on the way from ip -> memory that there is another initiator working now.

        :param task: Task entity contains all task properties
        :param mappings: List of mappings of task
        :return: resource (Basically executing unit or driver), SchedulingState.
        """
        if not mappings:
            # Empty mappings -> task is not mapped to any.
            self._update_unmapped_task(task)
            return None, SchedulingState.NULL

        resource = None
        for mapping in mappings:
            resource = mapping.resource.schedule_task(task)
            if resource is not None:
                break
        if resource is None:
            return None, SchedulingState.NAN

        self._update_system(task, resource)
        return resource, SchedulingState.SCHEDULED

    def _update_unmapped_task(self, task):
        """
        Updating unmapped tasks runtime

        :param task:
        :return:
        """
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task.processing_cycles * GlobalClock.instance.period)

    def _update_proc_task(self, task, resource):
        """
        Updating processing tasks runtime

        :param task:
        :param resource:
        :return:
        """
        penalty = 1 if resource.ip.get_attribute(PENALTY) is None else resource.ip.get_attribute(PENALTY)
        runtime = task.processing_cycles * resource.clock.period * penalty
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, runtime)

    def _update_mem_task(self, task, resource):
        """
        Updating memory tasks

        :param task:
        :param resource:
        :return:
        """
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, 0)

    def _update_system(self, task, resource):
        """
        Updating system for running task on this resource

        :param task:
        :param resource:
        :return:
        """
        self._system_mgr.on_task_execute(task, resource)
        resource.ip.update_state()

    def on_task_finish(self, task):
        """
        On task finish handler

        :param task:
        :return:
        """
        resource = self._system_mgr.get_executing_task_resource(task)
        if resource is None:
            return

        resource.ip.on_task_finish(task, resource)

    def _get_task_resource(self, task):
        """
        Getting resource executes the task

        :param task:
        :return: Resource
        """
        return self._system_mgr.get_executing_task_resource(task)


class SystemScheduler:
    """
    System scheduler is system level scheduling chooses the mapping list appropriate for the task.

    It knows how to retrieve required mapping from system, where it's defined in mapping or by specific algo.
    Basically, users who wants to develop their own scheduler for mapping should
    inherit and override _get_task_mappings and/or schedule_task by required scheduling algo or mechanism .
    """
    def __init__(self, system_mgr, properties=None, platform_scheduler=None):
        self._system_mgr = system_mgr
        self._properties = properties if properties is not None else dict()
        self._platform_scheduler = platform_scheduler if platform_scheduler is not None \
            else BaseSystemScheduler(system_mgr)

    def schedule_task(self, task, resource=None):
        """
        Schedule task according to mapping which it retrieve from system manager.
        Scheduler will ask the system manager to get all task mappings and work accordingly.

        :param task: Task entity contains all task properties
        :param resource:
        :return: resource. Basically executing unit or driver.
        """
        mappings = self.get_task_mappings(task)
        return self._platform_scheduler.schedule_task(task, mappings)

    def get_task_mappings(self, task):
        """
        Getting task mappings

        :return: Mapping list
        """
        return self._system_mgr.mapping.get_task_mapping(task.name)

    def on_task_finish(self, task):
        """
        On task finish handler

        :param task:
        :return:
        """
        self._platform_scheduler.on_task_finish(task)

    def set_platform_scheduler(self, platform_scheduler):
        """
        Setting platform scheduler

        :param platform_scheduler:
        :return:
        """
        self._platform_scheduler = platform_scheduler


class BlockingScheduler(BaseSystemScheduler):
    """
    Blocking scheduler block the feature for tasks with the same id.

    Task which blocks the IP must have block_type attribute with block value and blocking_id attribute that indicates
    the allowed id to be scheduled.
    Task which unblocks the IP must have block_type attribute with unblock value.
    SchedulingState task to IP components with the following steps:

    - Checks if IP is blocked
        - If so, checks if task has the same blocking id that ip blocked in
            - If so, tried to map the task
        - If not, checks if the task is blocking
            - If so, block the ip with the proper blocking_id
            - If not, map the task normally
    """
    BLOCKING_TYPE = 'BLOCK_TYPE'
    BLOCKING_ID = 'BLOCK_ID'
    BLOCKING = 'BLOCKING'
    UNBLOCKING = 'UNBLOCKING'

    def __init__(self, properties=None):
        super().__init__(properties)

    def schedule_task(self, task, mappings=None):
        """
        Checks if the ip is blocked, and if the task has the relevant blocking id, and generates new mapping list

        :param task:
        :param mappings:
        :return:
        """
        if not mappings:
            return None, SchedulingState.NULL

        task_blocking_type = task.get_attribute(BlockingScheduler.BLOCKING_TYPE)
        task_blocking_id = task.get_attribute(BlockingScheduler.BLOCKING_ID, None)

        filtered_mappings = list()
        for mapping in mappings:
            ip = mapping.resource
            ip_blocking_id = ip.get_attribute(BlockingScheduler.BLOCKING_ID)

            # If the IP is blocked
            if ip_blocking_id is not None:
                if (task_blocking_id is not None and task_blocking_id ==
                        ip.get_attribute(BlockingScheduler.BLOCKING_ID)):
                    filtered_mappings.append(mapping)
            else:
                filtered_mappings.append(mapping)

        if not filtered_mappings:
            return None, SchedulingState.NAN

        resource, scheduling_state = super().schedule_task(task, filtered_mappings)
        if resource is None:
            return resource, scheduling_state
        ip = resource.ip

        # If the task is blocking then it needs to block the ip it was scheduled to
        if task_blocking_type == BlockingScheduler.BLOCKING:
            if task_blocking_id is None:
                raise ValueError('Blocking task should have BLOCK_ID attribute')
            ip.attach_attribute(BlockingScheduler.BLOCKING_ID, task_blocking_id)
        return resource, scheduling_state

    def on_task_finish(self, task):
        """
        Once task finish need to check if it has unblock attribute. if so need to update the ip accordingly.

        :param task:
        :return:
        """
        ip = self._system_mgr.get_executing_task_resource(task).ip
        if ip is None:
            return super().on_task_finish(task)
        task_blocking_type = task.get_attribute(BlockingScheduler.BLOCKING_TYPE)
        task_blocking_id = task.get_attribute(BlockingScheduler.BLOCKING_ID)
        # If the task is unblocking and the ip is blocked, need to unblock it
        if task_blocking_type == BlockingScheduler.UNBLOCKING:
            if task_blocking_id is None:
                raise ValueError('Unblocking task should have UNBLOCK_ID attribute')

            if task_blocking_id == ip.get_attribute(BlockingScheduler.BLOCKING_ID):
                # If the ID's match than the task unblocks the ip
                ip.attach_attribute(BlockingScheduler.BLOCKING_ID, None)

        return super().on_task_finish(task)


class SplitScheduler(BaseSystemScheduler):
    SPLIT_COUNTER = 'SPLIT_COUNTER'

    def __init__(self, properties=None):
        super().__init__(properties)
        self._task_to_resource = dict()

    def schedule_task(self, task, mappings=None):
        """
        Schedules task according to a designated resource if it's not the first split, if it is it sets the designated
        resource

        :param task:
        :param mappings:
        :return:
        """
        designated_resource = self._task_to_resource.get(task, None)
        if designated_resource is None:
            # Here we don't have a designated resource
            resource, scheduling_state = super().schedule_task(task, mappings)
            if resource is not None:
                self._task_to_resource[task] = resource.ip
            return resource, scheduling_state
        else:
            # Here we do have a designated resource
            return super().schedule_task(task, [MappingEntity(task, designated_resource)])

    def on_task_finish(self, task):
        """
        Updating the split count on the task and if it's reached the amount of splits, the designated resource for this
        task id is being deleted

        :param task:
        :return:
        """
        task_split_counter = task.get_attribute(SplitScheduler.SPLIT_COUNTER, 1)
        if task_split_counter == task.get_attribute(TASK_SPLIT_COUNT, 1):
            if self._task_to_resource.get(task) is not None:
                del self._task_to_resource[task]
            task.attach_attribute(SplitScheduler.SPLIT_COUNTER, 1)
        else:
            task.attach_attribute(SplitScheduler.SPLIT_COUNTER, task_split_counter + 1)

        return super().on_task_finish(task)


class RPWScheduler(SplitScheduler):
    """
    Schedule read-proc-write tasks according to the read task.

    Which means that the read process and write tasks will all be scheduled to the same resource
    """
    def __init__(self, properties=None):
        super().__init__(properties)
        self._wltask_to_resource = dict()

    def schedule_task(self, task, mappings=None):
        """
        Schedules the first task with the same wltask normally, and all the other tasks maps to same one.

        :param task:
        :param mappings:
        :return:
        """
        wltask_name = task.get_attribute(WLTASK_NAME)
        if wltask_name is None or mappings is None or not mappings:
            return super().schedule_task(task, mappings)
        designated_resource = self._wltask_to_resource.get(wltask_name, None)
        if designated_resource is None:
            # Here we don't have a designated resource
            resource, scheduling_state = super().schedule_task(task, mappings)
            if resource is not None:
                self._wltask_to_resource[wltask_name] = resource.ip
            return resource, scheduling_state
        else:
            # Here we do have a designated resource
            return super().schedule_task(task, [MappingEntity(task, designated_resource)])

    def on_task_finish(self, task):
        """
        If the task is write task and have a wltask parent, reset it's designated resource

        :param task:
        :return:
        """
        wltask_name = task.get_attribute(WLTASK_NAME)
        if wltask_name is not None and task.type == TYPES.WRITE and \
                self._wltask_to_resource.get(wltask_name) is not None:
            del self._wltask_to_resource[wltask_name]

        return super().on_task_finish(task)
