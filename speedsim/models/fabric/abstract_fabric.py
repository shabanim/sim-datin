from collections import namedtuple

from pandas import DataFrame

from asap.ips import IP
from asap.strings import (MEMORY_PATH, NAME_SEPARATOR, RESOURCE, TASK, TYPE,
                          MappingDesc, ResourceDesc, TaskMetaData)
from asap.workload import TYPES
from pnets.simulation import EVENTS
from post_processing.utils import (convert_heartbeat_to_interval_table,
                                   get_hw_analysis)
from speedsim_utils import Logger

# Fabric Extension data
BUSBWEvent = namedtuple('BWEvent', ('TIME', 'BUS', 'BW', 'SOURCE'))
BUSBWInterval = ['START', 'FINISH', 'BUS', 'BW']
DriverBWEvent = namedtuple('BWEvent', ('TIME', 'RESOURCE', 'BW', 'TARGET'))


class FabricExtension:
    """
    Fabric extensions adds awareness of data movement to the simulation.
    Samples system each time task execute/finish, updates buses and adjust running tasks runtime accordingly.
    """
    BW = "BW"

    def __init__(self, sim, system_mgr):
        self._sim = sim
        self._system_mgr = system_mgr
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_task_execute)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)
        self._sim.connect_to_event(EVENTS.TASK_UPDATE, self._update_tasks)
        self._bus_bw_events = list()
        self._driver_bw_events = list()

    def _get_task(self, transition):
        """
        Getting task of speedSim transition
        :param transition:
        :return: Task
        """
        return transition.get_pnml_attribute(TASK)

    def _handle_task(self, transition):
        """
        Handles the task by updating the speedsim Transition runtime according to it
        :param transition:
        :return:
        """
        transition.runtime = self._get_task(transition).get_attribute(TaskMetaData.TASK_RUNTIME)

    def _get_resource(self, resource):
        """
        Getting platform resource out of speedsim resource
        :param resource:
        :return:
        """
        if resource is None or resource.resource_type == 'NULL':
            return None
        return resource.get_attribute(RESOURCE)

    def get_task_mem_target(self, task, resource):
        """
        Getting task memory target. if it does specify any target then choose first memory its resource can reach
        :param task:
        :param resource:
        :return:
        """
        memory_targets = task.get_attribute(MappingDesc.MEMORY_TARGETS, dict())
        if memory_targets == dict():
            one_target = task.get_attribute(MappingDesc.MEMORY_TARGET, None)
            if one_target is not None:
                return {one_target: 100}
            for mem in self._system_mgr.sys_platform.memories:
                if not self._system_mgr.sys_platform.get_routing_path(resource.ip, mem):
                    memory_targets[task.get_attribute(MappingDesc.MEMORY_TARGET, mem.name)] = 100
                    break
        return memory_targets

    def on_task_execute(self, transition, resource):
        """
        Will be called each time task want to start running (after scheduling succeeded)
        :param transition:
        :param resource:
        :return:
        """
        task = self._get_task(transition)
        if task is None or task.type == TYPES.PROC or task.type == TYPES.GEN:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if not self._system_mgr.sys_platform.memories:
            return

        mem_name = task.get_attribute(MappingDesc.MEMORY_TARGET)
        mem_name = mem_name if mem_name is not None else self._system_mgr.sys_platform.memories[0].name
        self._activate_routing_path(task, hw_resource, mem_name)
        min_bw, saved_route_path = self._get_min_bw(hw_resource.ip, mem_name, task.get_attribute('ROUTE_PATH', None))

        self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                    RESOURCE=hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name,
                                                    BW=min_bw,
                                                    TARGET=mem_name))
        data = task.read_bytes + task.write_bytes
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, data/min_bw)
        task.attach_attribute(self.BW, min_bw)
        self._update_tasks(transition, min_bw)

    def on_task_finish(self, transition, resource):
        """
        Will be called each time a task has finished
        :param transition:
        :param resource:
        :return:
        """
        task = transition.get_pnml_attribute(TASK)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            return
        routing_path = task.get_attribute(MEMORY_PATH, None)
        mem_name = task.get_attribute(MappingDesc.MEMORY_TARGET)
        mem_name = mem_name if mem_name is not None else self._system_mgr.sys_platform.memories[0].name
        min_bw, saved_route_path = self._get_min_bw(hw_resource.ip, mem_name, routing_path)
        self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                    RESOURCE=hw_resource.ip.name + NAME_SEPARATOR + hw_resource.name,
                                                    BW=0,
                                                    TARGET=mem_name))
        self._deactivate_routing_path(hw_resource, mem_name, routing_path)
        self._update_tasks(transition, min_bw)

    def _get_min_bw(self, source, mem_name, route_path=None):
        """
        Getting minimum bandwidth of buses in the path from source to memory
        :param source:
        :param mem_name:
        :return: bw
        """
        if mem_name is None:
            print("Can't find memory without name!")
            return
        target = self._system_mgr.sys_platform.get_memory(mem_name)
        if target is None:
            print("Did not find memory with name ", mem_name)
            return
        if route_path is None:
            route_path = self._system_mgr.sys_platform.get_routing_path(source, target)
            route_path = route_path[1:-1]
        min_bw = target.bw
        prev_bus = None
        prev_bw = None
        for bus_name in route_path:
            bus = self._system_mgr.sys_platform.get_bus(bus_name[0])
            bw = bus.bw
            if prev_bus is None:
                if isinstance(source, IP):
                    self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=bw,
                                                          SOURCE=source.name))
                else:
                    self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=bw,
                                                          SOURCE=source.ip.name + NAME_SEPARATOR + source.name))
            else:
                self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=prev_bw,
                                                      SOURCE=prev_bus.name))
            if min_bw is None:
                min_bw = bw
            if bw < min_bw:
                min_bw = bw
            prev_bus = bus
            prev_bw = bw
        return min_bw, route_path

    def _activate_routing_path(self, task, resource, target_mem):
        """
        Activate initiators of buses on all routing path from resource to task memory targets.
        Saves on task which buses and memory its targeting
        :param task:
        :param resource:
        :return:
        """
        Logger.log(self._sim.now, 'FabricExtension, Activating routing path - from source: '
                   + resource.ip.name + NAME_SEPARATOR + resource.name
                   + ' to target: ' + target_mem)
        if target_mem is None:
            return
        else:
            target = self._system_mgr.sys_platform.get_memory(target_mem)

        if target is None:
            Logger.log(self._sim.now, 'Target was not found!')
            return

        route_path = task.get_attribute(MEMORY_PATH, None)
        if route_path is None:
            route_path = self._system_mgr.sys_platform.get_routing_path(resource.ip, target)
            route_path = route_path[1:-1]
        Logger.log(self._sim.now, 'Activating path: ' + str(route_path))

        prev = None
        for bus_name in route_path:
            if isinstance(bus_name, tuple):
                bus = self._system_mgr.sys_platform.get_bus(bus_name[0])
            else:
                bus = bus_name
            if prev is None:
                prev = resource
            bus.active_initiators[prev.name] += 1
            prev = bus
        task.attach_attribute(TaskMetaData.TASK_MEMORIES, [target])
        task.attach_attribute(TaskMetaData.TASK_ROUTING_PATH, [route_path])

    def _deactivate_routing_path(self, resource, target_mem, route_path=None):
        """
        Deactivate initiators of buses on all routing path from resource to memory target.
        :param resource:
        :param target_mem: target memory name
        :param route_path: # TODO: document
        :return:
        """
        Logger.log(self._sim.now, 'FabricExtension, Deactivating routing path - from source: '
                   + resource.ip.name + NAME_SEPARATOR + resource.name
                   + ' to target: ' + target_mem)
        if target_mem is None:
            return
        else:
            target = self._system_mgr.sys_platform.get_memory(target_mem)

        if target is None:
            Logger.log(self._sim.now, 'Target was not found!')
            return

        if route_path is None:
            route_path = self._system_mgr.sys_platform.get_routing_path(resource.ip, target)
            route_path = route_path[1:-1]
        Logger.log(self._sim.now, 'Deactivating path: ' + str(route_path))
        prev = None
        for bus_name in route_path:
            if isinstance(bus_name, tuple):
                bus = self._system_mgr.sys_platform.get_bus(bus_name[0])
            else:
                bus = bus_name
            if prev is None:
                prev = resource
            bus.active_initiators[prev.name] -= 1
            if bus.active_initiators[prev.name] == 0:
                del bus.active_initiators[prev.name]
                self._bus_bw_events.append(BUSBWEvent(TIME=self._sim.now, BUS=bus.name, BW=0,
                                                      SOURCE=prev.name))
            prev = bus

    def _update_tasks(self, transition, min_bw):
        """
        Updating all currently executing tasks on the system.
        :param transition:
        :param min_bw:
        :return:
        """
        self._handle_task(transition)

        end_events = []
        read_write_tasks = [t for t in self._sim.get_executing_tasks() if
                            t[0].get_pnml_attribute(TYPE) != TYPES.PROC and t[0].get_pnml_attribute(
                                TYPE) != TYPES.GEN]
        for executed_task in read_write_tasks:
            if executed_task[0] == transition:
                continue
            event = executed_task[0].end_event
            if event is not None and event.name == EVENTS.TASK_END:
                t = self._get_task(executed_task[0])
                if t is None:
                    continue
                r = executed_task[1].get_attribute(RESOURCE)
                if r is None:
                    continue
                mem_name = t.get_attribute(MappingDesc.MEMORY_TARGET)
                mem_name = mem_name if mem_name is not None else self._system_mgr.sys_platform.memories[0].name
                min_bw, saved_route_path = self._get_min_bw(r.ip, mem_name, t.get_attribute(MEMORY_PATH))
                bw = t.get_attribute(self.BW, min_bw)
                remaining_time = event.clock - self._sim.now
                diff = ((remaining_time * (bw / min_bw)) - remaining_time)
                event.clock += diff
                t.attach_attribute(self.BW, min_bw)
                end_events.append(event)
                t_runtime = t.get_attribute(TaskMetaData.TASK_RUNTIME)
                t.attach_attribute(TaskMetaData.TASK_RUNTIME, t_runtime + diff)
                self._driver_bw_events.append(DriverBWEvent(TIME=self._sim.now,
                                                            RESOURCE=r.ip.name + NAME_SEPARATOR + r.name,
                                                            BW=min_bw,
                                                            TARGET=mem_name))
                self._handle_task(executed_task[0])

        # Update events according to new times
        for event in end_events:
            self._sim.update_event(event)

    def get_driver_bw_events(self):
        driver_bw_events = DataFrame(self._driver_bw_events)
        driver_bw_events.drop_duplicates(['TIME', 'RESOURCE', 'TARGET'], 'last')
        return driver_bw_events

    def get_bus_bw_events(self):
        bus_bw_events = DataFrame(self._bus_bw_events)
        bus_bw_events.drop_duplicates(['TIME', 'BUS', 'SOURCE'], 'last')
        return bus_bw_events

    def get_bus_bw_intervals(self):
        """
        Returns bus bandwidth intervals by source
        :return: Dataframe
        """
        return convert_heartbeat_to_interval_table(self.get_bus_bw_events(), ['BUS', 'SOURCE'], 'BW')

    def get_driver_bw_intervals(self):
        """
        Returns driver bandwidth intervals by target
        :return: Dataframe
        """
        driver_events = self.get_driver_bw_events()
        # Adding 0 BW events whenever there is a change in target
        driver_events_list = list()
        resource_to_target = dict()
        for index, row in driver_events.iterrows():
            resource = row['RESOURCE']
            last_target = resource_to_target.get(resource)
            if last_target is None:
                resource_to_target[resource] = row['TARGET']
            elif last_target != row['TARGET']:
                driver_events_list.append([row['TIME'], row['RESOURCE'], 0, last_target])
                resource_to_target[resource] = row['TARGET']
            driver_events_list.append([row['TIME'], row['RESOURCE'], row['BW'], row['TARGET']])
        driver_events = DataFrame(driver_events_list, columns=['TIME', 'RESOURCE', 'BW', 'TARGET'])
        driver_bw_intervals = convert_heartbeat_to_interval_table(driver_events,
                                                                  ['RESOURCE', 'TARGET'], 'BW')
        return driver_bw_intervals[driver_bw_intervals['BW'] != 0]

    def get_bw_intervals(self):
        """
        Returns tables with of START, FINISH, RESOURCE, TARGET, BW for driver
        and START, FINISH, BUS, BW, SOURCE for bus
        :return: bus & ip data frames
        """
        return self.get_bus_bw_intervals(), self.get_driver_bw_intervals()

    @staticmethod
    def _get_resource_target_name(resource_name, target_name):
        return resource_name + NAME_SEPARATOR + target_name

    def get_effective_bandwidth_table(self, hw_type, start=0, end=None, intervals=1):
        """
        Returns the effective bandwidth analysis table
        :param hw_type: ResourceDesc.MEMORY or ResourceDesc.BUS or ResourceDesc.DRIVER
        :param start: start time
        :param end: end time
        :param intervals: amount of intervals
        :return: proper HW type Data frame result
        """
        if hw_type == ResourceDesc.BUS:
            runtime_table, res_table = get_hw_analysis(ResourceDesc.BUS, start, end, intervals)
            for bus_name, row in res_table.iterrows():
                for time_frame in res_table.columns:
                    bus = self._system_mgr.sys_platform.get_bus(bus_name)
                    res_table[time_frame][bus_name] = bus.out_bw * res_table[time_frame][bus_name] / 100

        elif hw_type == ResourceDesc.MEMORY:
            runtime_table, res_table = get_hw_analysis(ResourceDesc.MEMORY, start, end, intervals)
            for mem_name, row in res_table.iterrows():
                for time_frame in res_table.columns:
                    memory = self._system_mgr.sys_platform.get_memory(mem_name)
                    res_table[time_frame][mem_name] = memory.bw * res_table[time_frame][mem_name] / 100

        elif hw_type == ResourceDesc.DRIVER:
            from post_processing.utils import get_average_value_table
            runtime_table = self.get_driver_bw_intervals()
            res_table = get_average_value_table(runtime_table, 'RESOURCE', 'BW', start, end, intervals)
        else:
            raise ValueError("HW type need to be either ResourceDesc.MEMORY, ResourceDesc.BUS or ResourceDesc.Driver!")

        return res_table

    def get_real_memories_data_table(self, start=0, end=None, intervals=1):
        """
        Returns the average bandwidth of the memories by the actual data that has been read per interval
        :param start:
        :param end:
        :param intervals:
        :return: DataFrame
        """
        from post_processing.utils import get_average_value_table
        memory_table = self.get_driver_bw_intervals()
        return get_average_value_table(memory_table, 'TARGET', 'BW', start, end, intervals)
