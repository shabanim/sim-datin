import math

from asap.strings import (TASK_ACTIVATION_COUNT, TASK_SPLIT_COUNT, MappingDesc,
                          TaskMetaData)
from asap.workload import TYPES
from models.fabric.multi_memory import MultiMemoryExtension

# TODO: Saeed - get rid of duplicated in below 2 extensions


class MTLNearFarFabric(MultiMemoryExtension):
    """
    Fabric that calculates the drain task time according to the fill task time
    Uses the DISPLAY_TYPE attribute on drain and fill tasks
    """

    def __init__(self, sim, system_mgr):
        super().__init__(sim, system_mgr)
        self._drain_time = 0

    def on_task_execute(self, transition, resource):
        task = self._get_task(transition)
        if task is None:
            return super().on_task_execute(transition, resource)

        display_type = task.get_attribute('DISPLAY_TYPE', None)
        if display_type is not None and display_type == 'drain':
            cycle_time = task.get_attribute('CYCLE_TIME')
            task.attach_attribute(TaskMetaData.TASK_RUNTIME, cycle_time - self._drain_time)
            self._handle_task(transition)
        elif task.type == TYPES.READ or task.type == TYPES.WRITE:

            # print('Debug1', transition.transition.id)
            orig_targets = task.get_attribute('ORIGINAL_MEMORY_TARGETS')
            if orig_targets is None:
                orig_targets = task.get_attribute('MEMORY_TARGETS_SPLIT_DISTRIBUTION', dict())
                task.attach_attribute('ORIGINAL_MEMORY_TARGETS', orig_targets)
                round_size = sum(list(orig_targets.values()))
                task.attach_attribute('ROUND_SIZE', round_size)
                # print('Debug1.1 orig targets: ', orig_targets)

            # print('Debug2')
            if orig_targets != dict():
                activation_count = task.get_attribute(TASK_ACTIVATION_COUNT, 0)
                split_count = task.get_attribute(TASK_SPLIT_COUNT, 1)
                # print('Debug3 activation count:', activation_count, 'Split count', split_count)
                if split_count > 1:
                    activations = 0
                    round_size = task.get_attribute('ROUND_SIZE', sum(list(orig_targets.values())))
                    # print('Debug4 round size: ', round_size)
                    if activation_count == round_size:
                        # task.attach_attribute(TASK_ACTIVATION_COUNT, 0)
                        activation_count = 0
                    # print('Debug3.1 activation count:', activation_count, 'Split count', split_count)
                    for target, percent in orig_targets.items():
                        activations += percent
                        # print('mems acts are: ', activations, '| on target:', target)
                        if activation_count < activations:
                            # print('going to memory', target, 'for 100%', 'for activation', activation_count)
                            task.attach_attribute(MappingDesc.MEMORY_TARGETS, {target: 100})
                            task.attach_attribute(TASK_ACTIVATION_COUNT, activation_count+1)
                            break
                # print('Debug5')
        # print('Debug6')
        return super().on_task_execute(transition, resource)

    def on_task_finish(self, transition, resource):
        task = self._get_task(transition)
        if task is not None:
            display_type = task.get_attribute('DISPLAY_TYPE')
            if display_type is not None and display_type == 'fill':
                self._drain_time = task.get_attribute(TaskMetaData.TASK_RUNTIME)

        return super().on_task_finish(transition, resource)


class MTLNearFarFabricMemDistribution(MultiMemoryExtension):
    """
    Fabric that calculates the drain task time according to the fill task time
    Uses the DISPLAY_TYPE attribute on drain and fill tasks
    Its also sensitive to data amount on each split.
    """

    def __init__(self, sim, system_mgr):
        super().__init__(sim, system_mgr)
        self._drain_time = 0

    def on_task_execute(self, transition, resource):
        task = self._get_task(transition)
        if task is None:
            return super().on_task_execute(transition, resource)

        display_type = task.get_attribute('DISPLAY_TYPE', None)
        if display_type is not None and display_type == 'drain':
            cycle_time = task.get_attribute('CYCLE_TIME')
            task.attach_attribute(TaskMetaData.TASK_RUNTIME, cycle_time - self._drain_time)
            self._handle_task(transition)
        elif task.type == TYPES.READ or task.type == TYPES.WRITE:
            # print('Debug1 - Task name:', transition.transition.id)
            total_data = task.get_attribute('TOTAL_DATA', None)
            if total_data is None:
                split_count = task.get_attribute(TASK_SPLIT_COUNT, 1)
                total_data = task.read_bytes if task.type == TYPES.READ else task.write_bytes
                total_data *= split_count
                task.attach_attribute('TOTAL_DATA', total_data)
                # print('Debug 1.1 - Retrieving total data first time.')
            # print('Debug2 - Task total data', total_data)

            tasks_distribution = task.get_attribute('MEMORY_TARGETS_DISTRIBUTION', None)
            if tasks_distribution is not None:
                activation_count = task.get_attribute(TASK_ACTIVATION_COUNT, 0)
                split_count = task.get_attribute(TASK_SPLIT_COUNT, 1)
                # print('Debug3 - Activation count:', activation_count, ', Split count', split_count)
                if activation_count == split_count:
                    activation_count = 0
                mem_info = tasks_distribution[activation_count] \
                    if activation_count < len(tasks_distribution) else tasks_distribution[-1]
                # print('Debug 4 - Memory info: ', mem_info)
                if task.type == TYPES.READ:
                    task.read_bytes = math.ceil((total_data * mem_info.get('DATA_PORTION', 100)) / 100)
                    # print('Debug 5.1 - Read task with: ', task.read_bytes)
                else:
                    task.write_bytes = math.ceil((total_data * mem_info.get('DATA_PORTION', 100)) / 100)
                    # print('Debug 5.2 - Write task with: ', task.write_bytes)

                task.attach_attribute(MappingDesc.MEMORY_TARGETS, mem_info.get(MappingDesc.MEMORY_TARGETS))
                task.attach_attribute(TASK_ACTIVATION_COUNT, activation_count + 1)
        return super().on_task_execute(transition, resource)

    def on_task_finish(self, transition, resource):
        task = self._get_task(transition)
        if task is not None:
            display_type = task.get_attribute('DISPLAY_TYPE')
            if display_type is not None and display_type == 'fill':
                self._drain_time = task.get_attribute(TaskMetaData.TASK_RUNTIME)

        return super().on_task_finish(transition, resource)
