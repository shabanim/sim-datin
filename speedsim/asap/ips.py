"""
IPs and their internal components definition. IP includes:
    - Executing unit: responsible for executing only
    - Driver: Aware of data
    - Port: IP connections

IP supports IP state:
    - Power State
    - Active state
"""
from typing import List

from .hw import (Clock, ComponentState, ConnectableHWComponent,
                 GeneralHWComponent, TickingHWComponent)
from .schedulers import IPScheduler, Scheduler
from .states import ActiveState, Condition, Expression, HierarchyState
from .strings import ATTRIBUTES, ComponentDesc, ResourceDesc, StateDesc
from .workload import Task


class ExecutingUnit(TickingHWComponent):
    """
    Executing component, knows how to execute only.

    Each executing unit can handle one task per time.
    Supporting power states.

    :param name: Unit name
    :param clock: Clock
    :param ip: Parent
    """
    def __init__(self, name, clock: Clock, ip=None, scheduler=None, power_states=None, active_state=None, forces=None,
                 constraints=None):
        super().__init__(name=name, clock=clock, _type=ResourceDesc.EX_U, power_states=power_states,
                         active_state=active_state, forces=forces, constraints=constraints)
        self._ip = ip
        self._executing_task = None
        self._scheduler = scheduler if scheduler is not None else Scheduler()

    @property
    def ip(self):
        """
        :return: parent ip
        """
        return self._ip

    @ip.setter
    def ip(self, ip):
        """
        Setting parent ip

        :param ip:
        :return:
        """
        self._ip = ip

    @property
    def executing_task(self):
        """
        :return: Currently executing task
        """
        return self._executing_task

    @executing_task.setter
    def executing_task(self, task):
        """
        Setting currently executing task

        :param task:
        :return:
        """
        self._executing_task = task

    def schedule_task(self, task: Task):
        """
        Schedule task on self resource

        :param task: Task object
        :return: True if succeeded, False otherwise.
        """
        return self._scheduler.schedule_task(task, self)

    def on_task_finish(self, task=None):
        """
        If there is any thing to do once task finish running on self resource, e.g. setting state to FREE.

        :param task:
        :return:
        """
        self._scheduler.on_task_finish(self)

    def to_dict(self):
        return super().to_dict()

    @staticmethod
    def load(desc, clocks):
        """
        Creates a new executing unit from an executing unit dictionary representation

        :param desc: a dict representing an eu {<name>: {'Clock': <clock_name>}}
        :param clocks: list of clocks
        :return: Executing Unit
        """
        name = list(desc.keys())[0]
        clk = None
        for clock in clocks:
            if clock.name == desc[name][ComponentDesc.CLOCK]:
                clk = clock
                break
        if clk is None:
            raise ValueError('Clock: ', desc[name][ComponentDesc.CLOCK], ' in executing unit', name, 'does not exist!.')
        ex = ExecutingUnit(name, clk,
                           power_states=TickingHWComponent.
                           load_power_states(desc[name].get(StateDesc.POWER_STATES)),
                           active_state=ActiveState.load(desc[name].get(StateDesc.ACTIVE_STATE)),
                           forces=[HierarchyState.load(force) for force in desc[name].get(StateDesc.FORCES, list())],
                           constraints=[HierarchyState.load(constraint) for constraint in
                                        desc[name].get(StateDesc.CONSTRAINTS, list())])
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            ex.attach_attribute(attr, value)
        return ex


class Port(ConnectableHWComponent):
    """
    Port component - connecting internal ip components to external world.

    :param name: Port name
    :param ip: Parent
    :param initiators: [list] -> should be from IP internal world - like drivers -
    :param targets: [list] -> should be from external world - like buses -
    """
    def __init__(self, name, ip=None, initiators=None, targets=None):
        super().__init__(name=name, initiators=initiators, targets=targets, _type=ResourceDesc.PORT)
        self._ip = ip

    @property
    def ip(self):
        """
        :return: parent ip
        """
        return self._ip

    @ip.setter
    def ip(self, ip):
        """
        Setting parent ip

        :param ip:
        :return:
        """
        self._ip = ip

    def to_dict(self):
        return super().to_dict()

    @staticmethod
    def load(desc):
        """
        Creates a new port from a port dictionary representation

        :param desc: a dict representing a port {<name>: {'Initiators': <list>, 'Targets': <list>}}
        :return: Port
        """
        name = list(desc.keys())[0]
        port = Port(name)
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            port.attach_attribute(attr, value)
        return port


class Driver(GeneralHWComponent):
    """
    Driver component, aware of traffic and its handling. Supporting power states.

    :param name: Driver name
    :param clock: Clock
    :param ports: Ports list driver is connected to
    :param ip: Parent IP the driver is in
    """
    def __init__(self, name, clock: Clock, ports: List[Port] = None, ip=None, scheduler=None, power_states=None,
                 active_state=None, forces=None, constraints=None):
        super(Driver, self).__init__(name, clock, _type=ResourceDesc.DRIVER, targets=ports, power_states=power_states,
                                     active_state=active_state, forces=forces, constraints=constraints)
        self._ip = ip
        self._executing_task = None
        self._scheduler = scheduler if scheduler is not None else Scheduler()

    @property
    def ip(self):
        """
        :return: parent ip
        """
        return self._ip

    @ip.setter
    def ip(self, ip):
        """
        Setting parent ip

        :param ip:
        :return:
        """
        self._ip = ip

    @property
    def executing_task(self):
        """
        :return: Currently executing task
        """
        return self._executing_task

    @executing_task.setter
    def executing_task(self, task):
        """
        Setting currently executing task

        :param task:
        :return:
        """
        self._executing_task = task

    def schedule_task(self, task: Task):
        """
        Schedule task on self resource

        :param task:
        :return: True if succeeded, False otherwise.
        """
        return self._scheduler.schedule_task(task, self)

    def on_task_finish(self, task=None):
        """
        If there is any thing to do once task finish running on self resource, like setting state to FREE.

        :param task:
        :return:
        """
        self._scheduler.on_task_finish(self)

    def to_dict(self):
        return super().to_dict()

    @staticmethod
    def load(desc, clocks):
        """
        Creates a new driver from driver dictionary representation

        :param desc: a dict representing a driver {<name>: {'Clock': <clock_name>, 'Initiators': <list>,
                                                            'Targets': <list>}}
        :param clocks: list of clocks
        :return: Driver
        """
        name = list(desc.keys())[0]
        clk = None
        for clock in clocks:
            if clock.name == desc[name][ComponentDesc.CLOCK]:
                clk = clock
                break
        if clk is None:
            raise ValueError('Clock: ', desc[name][ComponentDesc.CLOCK], ' in driver ', name, 'does not exist!.')
        dr = Driver(name, clk,
                    power_states=TickingHWComponent.load_power_states(desc[name].get(StateDesc.POWER_STATES)),
                    active_state=ActiveState.load(desc[name].get(StateDesc.ACTIVE_STATE)),
                    forces=[HierarchyState.load(force) for force in desc[name].get(StateDesc.FORCES, list())],
                    constraints=[HierarchyState.load(constraint) for constraint in
                                 desc[name].get(StateDesc.CONSTRAINTS, list())])
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            dr.attach_attribute(attr, value)
        return dr


class IP(GeneralHWComponent):
    """
    IP Component, contains:
        - Drivers for traffic
        - Executing units for computing
        - Ports for connections
        - Scheduler - responsible for scheduling tasks to ip internal components
        - Power and Active states

    :param name: IP name
    :param executing_units: List of executing units
    :param drivers: List of drivers
    :param ports: List of ports
    :param clock: Clock
    :param scheduler: IP-Level scheduler
    :param connections: List of tuples, source->destination where source is driver and target is port
    :param ip_states: List of CStates ordered by the transition order
    """
    def __init__(self, name,
                 clock: Clock = None,
                 executing_units: List[ExecutingUnit] = None,
                 drivers: List[Driver] = None,
                 ports: List[Port] = None,
                 scheduler=None,
                 connections=None,
                 ip_states: List[HierarchyState] = None):
        super(IP, self).__init__(name, clock, ResourceDesc.IP)
        self._executing_units = executing_units if executing_units is not None else list()
        self._drivers = drivers if drivers is not None else list()
        self._ports = ports if ports is not None else list()
        self._scheduler = scheduler if scheduler is not None else IPScheduler()
        self._executing_tasks = dict()
        self._ip_states = ip_states if ip_states is not None else list()

        for component in self._executing_units + self._drivers + self._ports:
            component.ip = self

        if connections is not None:
            for src, dst in connections:
                dr = self.get_driver(src)
                p = self.get_port(dst)
                if dr is None or p is None:
                    continue
                self.connect_driver(dr, p)

    # Ports
    @property
    def ports(self):
        """
        :return: ports list
        """
        return self._ports

    def add_port(self, _port: Port):
        """
        Add new port to IP

        :param _port:
        :return:
        """
        for port in self._ports:
            if port.name == _port.name:
                raise ValueError("Port with name " + port.name + " already exists in this IP.")
        self._ports.append(_port)
        _port.ip = self

    def get_port(self, port_name):
        """
        Getting port by port name

        :param port_name:
        :return: Port with given name, None if does not exist.
        """
        for p in self._ports:
            if p.name == port_name:
                return p
        return None

    def del_port(self, port_name):
        """
        Deleting port with port name, nothing happens if port does not exist.

        :param port_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for port in self._ports:
            if port_name == port.name:
                to_del = port
                break
        if not to_del:
            self._ports.remove(to_del)
            return True
        return False

    # Drivers
    @property
    def drivers(self):
        """
        :return: drivers list
        """
        return self._drivers

    def add_driver(self, driver: Driver):
        """
        Add new driver to IP

        :param driver:
        :return:
        """
        for d in self._drivers:
            if d.name == driver.name:
                raise ValueError("Driver: " + driver.name + " already exists in this ip.")
        self._drivers.append(driver)
        driver._ip = self

    def get_driver(self, driver_name):
        """
        :param driver_name:
        :return: driver with given driver name, None if does not exist.
        """
        for driver in self._drivers:
            if driver_name == driver.name:
                return driver
        return None

    def del_driver(self, driver_name):
        """
        Delete driver with given name

        :param driver_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for driver in self._drivers:
            if driver_name == driver.name:
                to_del = driver
                break
        if not to_del:
            self._drivers.remove(to_del)
            return True
        return False

    # Executing units
    @property
    def executing_units(self):
        """
        :return: Executing units list
        """
        return self._executing_units

    def add_executing_unit(self, ex_unit: ExecutingUnit):
        """
        Adding new executing unit

        :param ex_unit:
        :return:
        """
        for ex in self._executing_units:
            if ex.name == ex_unit.name:
                raise ValueError("Execution unit: " + ex_unit.name + " already exists in this ip.")
        ex_unit._ip = self
        self._executing_units.append(ex_unit)

    def get_executing_unit(self, ex_u_name):
        """
        :param ex_u_name:
        :return: Executing unit with given name, None if does not exist.
        """
        for ex_u in self._executing_units:
            if ex_u_name == ex_u.name:
                return ex_u
        return None

    def del_executing_unit(self, ex_u_name):
        """
        Deleting executing unit with given name, nothing happens if it does not exist.

        :param ex_u_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for ex_u in self._executing_units:
            if ex_u_name == ex_u.name:
                to_del = ex_u
                break
        if not to_del:
            self._executing_units.remove(to_del)
            return True
        return False

    @property
    def ip_states(self):
        """
        :return: ips stats list, each ip state is of HierarchyState.
        """
        return self._ip_states

    @ip_states.setter
    def ip_states(self, ip_states):
        """
        Setting ip states

        :param ip_states:
        :return:
        """
        self._ip_states = ip_states

    def add_ip_state(self, ip_state):
        """
        Add new ip state to ips states list if does not exist, nothing happens if it does.

        :param ip_state: ip state is of HierarchyState class
        :return:
        """
        for state in self._ip_states:
            if state.name == ip_state.name:
                print('New IP state', ip_state.name, 'Already exists.')
                return
        self._ip_states.append(ip_state)

    def get_ip_state(self, ip_state_name):
        """
        Returns matching ip state

        :param ip_state_name:
        :return: IpState or None if not found
        """
        for state in self._ip_states:
            if state.name == ip_state_name:
                return state
        return None

    @property
    def initiators(self):
        """
        IP initiators, basically, ip ports initiators which are drivers.

        :return: list of drivers connected to ip ports.
        """
        return [port.initiators for port in self._ports]

    @property
    def targets(self):
        """
        IP targets, basically, ip ports targets which are buses.

        :return: list of buses ip connected to.
        """
        return [port.targets for port in self._ports]

    def connect_driver(self, driver: Driver, port: Port):
        """
        Connecting driver to port.

        :param driver:
        :param port:
        :return:
        """
        if port.ip.name != self.name:
            raise ValueError("Port: " + port.name + " is not part of this ip.")

        if driver.ip.name != self.name:
            raise KeyError("Driver: " + driver.name + " is not part of this ip.")

        driver.add_target(port)
        port.add_initiator(driver)

    def connect_port(self, port: Port, bus):
        """
        Connect to outer world from ip ports to system buses.

        :param port:
        :param bus:
        :return:
        """
        if port.ip.name != self.name:
            raise ValueError("Port: " + port.name + " is not part of this ip. aborted!")
        port.add_target(bus)
        bus.add_initiator(port)

    # Scheduling
    def schedule_task(self, task: Task):
        """
        Scheduling task on self. According to task type.
            - Proc task tries to find free executing unit
            - Data task tries to find free driver

        :param task:
        :return:
        """
        resource = self._scheduler.schedule_task(task, self)
        if resource is None:
            return None
        self._executing_tasks[task] = resource
        return resource

    def update_state(self):
        """
        Updating IP state to Free/Busy. If any internal component is busy then IP is busy, otherwise, its free.

        :return:
        """
        busy = False
        for comp in self.executing_units + self.drivers:
            if comp.state == ComponentState.BUSY:
                task = comp.executing_task
                if task not in self._executing_tasks:
                    self._executing_tasks[task] = comp
                busy = True
        if busy:
            self._state = ComponentState.BUSY
        else:
            self._state = ComponentState.FREE

    def on_task_finish(self, task, resource=None):
        """
        If there is any thing to do once task finish running on self resource, like setting state to FREE.

        :param task:
        :param resource:
        :return:
        """
        if resource is None:
            resource = self.get_resource_of_task(task)
        if resource is None:
            return

        resource.on_task_finish(task)
        self.update_state()
        if self._executing_tasks.get(task) is not None:
            del self._executing_tasks[task]

    def get_resource_of_task(self, task):
        """
        Getting resource that currently executing given task

        :param task:
        :return: Resources
        """
        return self._executing_tasks.get(task, None)

    def get_sleep_expression(self):
        """
        Returns an expression that is true only of all internal components of the IP are not in their active state

        :return: Expression
        """
        cond_list = list()
        for dr in self.drivers:
            cond_list.append(Condition(dr, StateDesc.EQUAL, dr.active_state.name, True))

        for ex in self.executing_units:
            cond_list.append(Condition(ex, StateDesc.EQUAL, ex.active_state.name, True))

        return Expression(self.name + 'Sleep', cond_list)

    def set_resource_to_task(self, task, resource):
        """
        Sets the task to this resource without limitation

        :param task:
        :param resource: internal resource of the ip
        :return:
        """
        self._executing_tasks[task] = resource

    def remove_task(self, task):
        """
        Removes the task from the resource

        :param task:
        :return:
        """
        del self._executing_tasks[task]

    def to_dict(self):
        """
        Converting ip to dict.

        :return: Dictionary
        """
        desc = TickingHWComponent.to_dict(self)
        desc[self.name][ComponentDesc.DRIVERS] = list()
        desc[self.name][ComponentDesc.EXEC_UNITS] = list()
        desc[self.name][ComponentDesc.PORTS] = list()
        desc[self.name][StateDesc.IP_STATES] = list()
        for driver in self.drivers:
            desc[self.name][ComponentDesc.DRIVERS].append(driver.to_dict())
        for ex_u in self.executing_units:
            desc[self.name][ComponentDesc.EXEC_UNITS].append(ex_u.to_dict())
        for port in self.ports:
            desc[self.name][ComponentDesc.PORTS].append(port.to_dict())
        for state in self.ip_states:
            desc[self.name][StateDesc.IP_STATES].append(state.to_dict())
        return desc

    @staticmethod
    def load(desc, clocks):
        """
        Creates an ip from ip dictionary representation

        :param desc: the dictionary that represents the ip: {<name>:{'Clock':<clock_name>, 'Ports':<port_list>,
                                                                    'Drivers':<driver_list>,
                                                                    'Executing units':<eu_list>}}
        :param clocks: list of clocks
        :return: IP
        """
        name = list(desc.keys())[0]
        clk = None
        for clock in clocks:
            if clock.name == desc[name][ComponentDesc.CLOCK]:
                clk = clock
                break
        if clk is None:
            raise ValueError('Clock: ', desc[name][ComponentDesc.CLOCK], ' in ip ', name, 'does not exist!.')
        ip = IP(name, clk, list(), list(), list())
        for eu_desc in desc[name][ComponentDesc.EXEC_UNITS]:
            ip.add_executing_unit(ExecutingUnit.load(eu_desc, clocks))
        for port_desc in desc[name][ComponentDesc.PORTS]:
            ip.add_port(Port.load(port_desc))
        for driver_desc in desc[name][ComponentDesc.DRIVERS]:
            driver = Driver.load(driver_desc, clocks)
            ip.add_driver(driver)
            for connect_name in driver_desc[driver.name][ComponentDesc.TARGETS]:
                ip.connect_driver(driver, ip.get_port(connect_name[ComponentDesc.NAME]))
        ip_states = list()
        for ip_state_desc in desc[name].get(StateDesc.IP_STATES, list()):
            ip_states.append(HierarchyState.load(ip_state_desc))
        ip.ip_states = ip_states
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            ip.attach_attribute(attr, value)
        return ip


# IP Utils
def new_ip(ip_name, clock, execution_units, drivers, ports, clocks, connections):
    """
    Abstract function to create new IP. takes list of names and internally create required components.

    :param ip_name:
    :param clock: ip clock: Clock
    :param execution_units: List of execution units names
    :param drivers: List of drivers names
    :param ports: List of port names
    :param clocks: Dictionary of component -> clock: Clock
    :param connections: Dictionary of internal connections in the ip: driver -> port
    :return: IP
    """
    ex_units = list()
    for execution_unit in execution_units:
        ex_units.append(ExecutingUnit(execution_unit, clocks.get(execution_unit, None)))

    dr_units = dict()
    for driver in drivers:
        dr_units[driver] = Driver(driver, clocks.get(driver, None))

    ports_units = dict()
    for port in ports:
        ports_units[port] = Port(port)

    ip = IP(ip_name, clock, ex_units, list(dr_units.values()), list(ports_units.values()))
    for initiator, target in connections.items():
        driver = dr_units.get(initiator, None)
        if not driver:
            continue
        port = ports_units.get(target, None)
        if not port:
            continue
        driver.add_target(port)
        port.add_initiator(driver)
    return ip
