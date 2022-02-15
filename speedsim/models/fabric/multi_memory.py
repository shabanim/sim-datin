from collections import namedtuple

from asap.strings import (ACTIVE_RUNTIME, MEMORY_PATH, NAME_SEPARATOR,
                          RESOURCE, TYPE, MappingDesc, TaskMetaData)
from asap.workload import TYPES
from pnets.simulation import EVENTS
from speedsim import AnalysisExtension
from speedsim_utils import Logger

from .abstract_fabric import FabricExtension

BUSBWEvent = namedtuple('BWEvent', ('TIME', 'BUS', 'BW', 'SOURCE'))
MEMBWEvent = namedtuple('BWEvent', ('TIME', 'BUS', 'BW'))
DriverBWEvent = namedtuple('BWEvent', ('TIME', 'RESOURCE', 'BW', 'TARGET'))


class MultiMemoryExtension(FabricExtension):
    BW = 'BW'
    TARGETS_RUNTIME = 'TARGETS_RUNTIME'
    TASK_START_TIME = 'TASK_START_TIME'
    TARGET_IDX = 'TARGET_IDX'
    TARGETS_NUM = 'TARGETS_NUM'
    CHANGE_TARGET_EVENT = 'CHANGE_TARGET_EVENT'
    ADDITION_FAKE_TIME = 0.001

    def __init__(self, sim, system_mgr):
        super().__init__(sim, system_mgr)
        for bus in self._system_mgr.sys_platform.buses:
            bus.set_bw_func(bus.naive_bw_func)
        self.validator = None

    def on_task_execute(self, transition, resource):
        """
        Will be called each time task want to start running (after scheduling succeeded)
        Multiple memory extension assume that each task should define its memory targets.
        If no memory target defined then it will take the first memory its resource can reach as a target

        It starts with first memory target and add change event for the next memory target if exist.
        :param transition:
        :param resource:
        :return:
        """
        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            return

        if not self._system_mgr.sys_platform.memories:
            return

        Logger.log(self._sim.now, 'MultipleMemory, on task execute - task: ' + transition.transition.id +
                   ' | On resource: ' + hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name)

        memory_targets = self.get_task_mem_target(task, hw_resource)
        if memory_targets == dict():
            Logger.log(self._sim.now, 'MultipleMemory, on task execute - no memories can be reached')
            return
        Logger.log(self._sim.now, 'MultipleMemory, on task execute - memory targets ' + str(memory_targets))

        first_mem_target, first_data_percent, targets_num = self.validate_mem_percentage(task, memory_targets)
        # Handling only first memory target
        mem_targets_runtime = dict()
        task.attach_attribute(self.TARGETS_NUM, targets_num)
        task.attach_attribute(self.TARGET_IDX, 0)
        Logger.log(self._sim.now, 'MultipleMemory, on task execute - Handling first memory target: ' +
                   first_mem_target + ' | with data percentage: ' + str(first_data_percent))

        min_bw, saved_route_path = self._get_min_bw(hw_resource, first_mem_target)
        task.attach_attribute(MEMORY_PATH, saved_route_path)
        data = task.read_bytes if task.type == TYPES.READ else task.write_bytes
        if data == 0:
            return
        data_to_run_time = (first_data_percent / 100) * data / min_bw
        task_total_run_time = data_to_run_time
        mem_targets_runtime[first_mem_target] = data_to_run_time

        Logger.log(self._sim.now, 'MultipleMemory, on task execute - Task data: ' + str(data) +
                   ' | data runtime: ' + str(task_total_run_time) + ' | on min bw: ' + str(min_bw))

        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task_total_run_time)
        if self.validator is not None:
            self.validator.validate_task(task)
            task_total_run_time = task.get_attribute(TaskMetaData.TASK_RUNTIME)
        # Adding fake time to catch change event in time if there is more than one target.
        change_event = None
        if targets_num > 1 and task_total_run_time != 0:
            Logger.log(self._sim.now, 'MultipleMemory, on task execute - Adding change target event at time: '
                       + str(self._sim.now + data_to_run_time))
            task_total_run_time += self.ADDITION_FAKE_TIME
            mem_targets_runtime['FAKE'] = self.ADDITION_FAKE_TIME
            change_event = self._sim.insert_event(self.CHANGE_TARGET_EVENT, self._sim.now + data_to_run_time,
                                                  lambda: self._change_target(transition, resource))
            task.attach_attribute(self.CHANGE_TARGET_EVENT, change_event)

        task.attach_attribute(self.TASK_START_TIME, self._sim.now)
        self._activate_routing_path(task, hw_resource, first_mem_target)
        task.attach_attribute(self.BW, {first_mem_target: min_bw})
        task.attach_attribute(self.TARGETS_RUNTIME, mem_targets_runtime)

        # Re-Adjusting task runtime after activated routs
        time_diff = self._get_time_diff(task_total_run_time, {first_mem_target: 100}, hw_resource, task,
                                        self._sim.now + task_total_run_time)
        task_total_run_time += time_diff
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task_total_run_time)
        if change_event is not None:
            change_event.clock += time_diff
            self._sim.update_event(change_event)

        if self.validator is not None:
            self.validator.validate_task(task)
        self._sim.emit(EVENTS.TASK_UPDATE, transition)

    @staticmethod
    def validate_mem_percentage(task, memory_targets):
        """
        Validating memory targets data portion percentage if they sum to 100%.
        :param task:
        :param memory_targets:
        :return: raise error if not 100%. Otherwise, first memory target, first data percent, targets number.
        """
        # percentages checker
        total_percentage = 0
        first_mem_target = None
        first_data_percent = None
        first_done = False
        targets_num = 0
        for mem, percent in memory_targets.items():
            total_percentage += percent
            targets_num += 1
            if not first_done:
                first_mem_target = mem
                first_data_percent = percent
                first_done = True
        if total_percentage != 100:
            raise ValueError("The sum of data percent to targets in task " + task.name + " is: " + str(
                total_percentage) + ", it should be 100.")
        return first_mem_target, first_data_percent, targets_num

    def on_task_finish(self, transition, resource):
        """
        Will be called each time a task has finished
        :param transition:
        :param resource:
        :return:
        """
        task = self._get_task(transition)
        if task is None:
            return

        if resource is None or resource.resource_type == 'NULL':
            return

        hw_resource = resource.get_attribute(RESOURCE)
        if hw_resource is None:
            return

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            return

        task_runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME, 0)
        if task_runtime == 0:
            return

        Logger.log(self._sim.now, 'MultipleMemory, on task finish - task: ' + transition.transition.id +
                   ' | On resource: ' + hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name)

        memory_targets = self.get_task_mem_target(task, hw_resource)
        if memory_targets == dict():
            Logger.log(self._sim.now, 'MultipleMemory, on task finish - no memory targets.')
            return

        target_idx = task.get_attribute(self.TARGET_IDX, 0)
        target = list(memory_targets.keys())[target_idx]
        self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                    RESOURCE=hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name,
                                                    BW=0,
                                                    TARGET=target))
        self._deactivate_routing_path(hw_resource, target, task.get_attribute(MEMORY_PATH, None))
        self._sim.emit(EVENTS.TASK_UPDATE, transition)

    def _get_min_bw(self, source, mem_name, route_path=None):
        """
        Getting minimum seen by the source in its way to the target.
        For each bus, minimum BW is calculated according to minimum BW from the source to it,
        divided by it's active initiators
        """
        if mem_name is None:
            print("Can't find memory without name!")
            return
        target = self._system_mgr.sys_platform.get_memory(mem_name)
        if target is None:
            print("Did not find memory with name ", mem_name)
            return

        Logger.log(self._sim.now, 'MultipleMemory, on get min bw - source: ' + source.ip.name +
                   ' | memory: ' + mem_name)

        if route_path is None:
            route_path = self._system_mgr.sys_platform.get_routing_path(source.ip, target)
            route_path = route_path[1:-1]

        min_bw = None
        min_load_bw = target.bw
        prev_bus = None
        saved_route_path = list()
        for bus_name in route_path:
            if isinstance(bus_name, tuple):
                bus = self._system_mgr.sys_platform.get_bus(bus_name[0])
            else:
                bus = bus_name
            saved_route_path.append(bus)
            bus_load = len(bus.active_initiators.keys())
            bus_load = bus_load if bus_load != 0 else 1
            bw = bus.bw
            Logger.log(self._sim.now, 'MultipleMemory, on get min bw - bus: ' + str(bus_name) +
                       ' | bus_load: ' + str(bus_load) + ' | active initiators: ' +
                       str(sum(bus.active_initiators.values())))

            if min_bw is None or bw < min_bw:
                min_bw = bw
            bus_load_bw = min_bw / bus_load

            if min_load_bw is None or bus_load_bw < min_load_bw:
                min_load_bw = bus_load_bw

            if prev_bus is None:
                self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=bus_load_bw,
                                                      SOURCE=source.ip.name + NAME_SEPARATOR + source.name))
            else:
                if bus.active_initiators[prev_bus.name] == 0:
                    self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=0,
                                                          SOURCE=prev_bus.name))
                else:
                    self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=bus_load_bw,
                                                          SOURCE=prev_bus.name))
            prev_bus = bus
            Logger.log(self._sim.now, 'MultipleMemory, on get min bw - bus: ' + str(bus_name) +
                       ' | bus_load: ' + str(bus_load) + ' | active initiators: ' +
                       str(sum(bus.active_initiators.values())) + ' | bus BW: ' + str(bus_load_bw))
        if min_load_bw > target.bw:
            min_load_bw = target.bw

        Logger.log(self._sim.now, 'MultipleMemory, on get min bw - minimum BW: ' + str(min_load_bw))
        return min_load_bw, saved_route_path

    def _update_tasks(self, transition, min_bw=0):
        """
        Updates tasks after system change.
        :param transition: task caused system change
        :return
        """
        Logger.log(self._sim.now, 'MultipleMemory, updating tasks due to system change.')
        end_events = []
        if transition is not None:
            self._handle_task(transition)
        read_write_tasks = [t for t in self._sim.get_executing_tasks() if
                            t[0].get_pnml_attribute(TYPE) != TYPES.PROC and t[0].get_pnml_attribute(TYPE) != TYPES.GEN]
        for executed_task in read_write_tasks:
            Logger.log(self._sim.now, 'MultipleMemory, updating task: ' + executed_task[0].transition.id)
            if executed_task[0] == transition:
                continue
            event = executed_task[0].end_event
            if event is None or event.name != EVENTS.TASK_END:
                continue

            task = self._get_task(executed_task[0])
            if task.get_attribute(TaskMetaData.TASK_RUNTIME, 0) == 0:
                continue

            resource = executed_task[1].get_attribute(RESOURCE)
            if task is None or resource is None:
                continue

            targets = self.get_task_mem_target(task, resource)
            if targets == dict():
                continue

            # Adjusting time
            remaining_time = event.clock - self._sim.now
            time_diff = self._get_time_diff(remaining_time, targets, resource, task, event.clock)
            event.clock += time_diff
            Logger.log(self._sim.now, 'MultipleMemory, updating the remaining time to: ' +
                       str(remaining_time+time_diff) + ' | of task: ' + executed_task[0].transition.id)
            change_event = task.get_attribute(self.CHANGE_TARGET_EVENT)
            if change_event is not None:
                change_event.clock += time_diff
                end_events.append(change_event)
            t_runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME)
            task.attach_attribute(TaskMetaData.TASK_RUNTIME, t_runtime + time_diff)
            if self.validator is not None:
                self.validator.validate_task(task)
                n_runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME)
                if n_runtime != (t_runtime + time_diff):
                    event.clock += (n_runtime - (t_runtime + time_diff))
            self._handle_task(executed_task[0])
            end_events.append(event)

        # Update events according to new times
        for event in end_events:
            self._sim.update_event(event)

    def _change_target(self, transition, resource):
        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            return

        Logger.log(self._sim.now, 'MultipleMemory, changing target on task: ' + transition.transition.id +
                   ' | Running on resource: ' + hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name)

        mem_target_idx = task.get_attribute(self.TARGET_IDX, None)
        mem_targets = task.get_attribute(MappingDesc.MEMORY_TARGETS, dict())
        if mem_target_idx is None or mem_targets == dict():
            return

        prev_mem_target = list(mem_targets.keys())[mem_target_idx]
        self._deactivate_routing_path(hw_resource, prev_mem_target, task.get_attribute(MEMORY_PATH, None))
        self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, hw_resource, task, False)

        self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                    RESOURCE=hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name,
                                                    BW=0,
                                                    TARGET=prev_mem_target))

        active_time = task.get_attribute(ACTIVE_RUNTIME, 0)
        active_time += self._sim.now - task.get_attribute(self.TASK_START_TIME)
        task.attach_attribute(ACTIVE_RUNTIME, active_time)
        mem_target_idx += 1
        mem_target = list(mem_targets.keys())[mem_target_idx]
        data_percent = mem_targets[mem_target]

        targets_runtime = task.get_attribute(self.TARGETS_RUNTIME)
        min_bw, saved_route_path = self._get_min_bw(hw_resource, mem_target)
        task.attach_attribute(MEMORY_PATH, saved_route_path)
        data = task.read_bytes if task.type == TYPES.READ else task.write_bytes
        data_to_run_time = (data_percent / 100) * data / min_bw
        targets_runtime[mem_target] = data_to_run_time

        min_bw_per_target = task.get_attribute(self.BW) if task.get_attribute(self.BW) is not None \
            else {mem_target: min_bw}

        if (task.get_attribute(self.TARGETS_NUM)-1) > mem_target_idx:
            task.attach_attribute(self.CHANGE_TARGET_EVENT,
                                  self._sim.insert_event(self.CHANGE_TARGET_EVENT,
                                                         self._sim.now + data_to_run_time,
                                                         lambda: self._change_target(transition, resource)))
        else:
            if targets_runtime.get('FAKE', None) is not None:
                data_to_run_time -= self.ADDITION_FAKE_TIME
                del targets_runtime['FAKE']
                task.attach_attribute(self.CHANGE_TARGET_EVENT, None)

        task_runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME, 0) + data_to_run_time
        transition.end_event.clock += data_to_run_time
        self._sim.update_event(transition.end_event)
        task.attach_attribute(self.TARGET_IDX, mem_target_idx)
        task.attach_attribute(self.BW, min_bw_per_target)
        task.attach_attribute(self.TARGETS_RUNTIME, targets_runtime)
        task.attach_attribute(self.TASK_START_TIME, self._sim.now)
        self._activate_routing_path(task, hw_resource, mem_target)
        self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, hw_resource, task, True)
        task_runtime += self._get_time_diff(targets_runtime[mem_target], mem_targets, hw_resource, task,
                                            transition.end_event.clock)
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, task_runtime)
        if self.validator is not None:
            self.validator.validate_task(task)
        self._sim.emit(EVENTS.TASK_UPDATE, transition)

    def _get_time_diff(self, time, targets, resource, task, end_time):
        """
        Returns the difference in time according to the current min bandwith in each memory path
        :param time: time left for the task to run
        :param targets: targets dictionary, {target: percent}
        :param resource:
        :param task:
        :param end_time:
        """
        Logger.log(self._sim.now, 'MultipleMemory, getting time different of, time lef for the task: ' + str(time) +
                   ' | Running on resource: ' + resource.name + ' | of task: ' + task.name)
        targets_runtime = task.get_attribute(self.TARGETS_RUNTIME)
        task_last_start = task.get_attribute(self.TASK_START_TIME)
        current_time_of_task = (end_time - task_last_start) - time
        target_idx = task.get_attribute(self.TARGET_IDX, 0)
        target = list(targets.keys())[target_idx]

        active_runtime = task.get_attribute(ACTIVE_RUNTIME)
        if active_runtime is not None:
            for i in range(0, target_idx):
                active_runtime -= targets_runtime[list(targets.keys())[i]]
        else:
            active_runtime = 0
        # we have the target
        min_bw, saved_route_path = self._get_min_bw(resource, target, task.get_attribute(MEMORY_PATH, None))
        bw_dict = task.get_attribute(self.BW) if task.get_attribute(self.BW) is not None else {target: min_bw}
        bw = bw_dict.get(target, min_bw)
        task_remaining_time = targets_runtime[target] - current_time_of_task - active_runtime
        current_diff = task_remaining_time * (bw / min_bw) - task_remaining_time
        targets_runtime[target] += current_diff
        bw_dict[target] = min_bw
        task.attach_attribute(self.BW, bw_dict)
        task.attach_attribute(self.TARGETS_RUNTIME, targets_runtime)
        self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                    RESOURCE=resource.ip.name + NAME_SEPARATOR + resource.name,
                                                    BW=min_bw,
                                                    TARGET=target))
        return current_diff
