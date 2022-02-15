"""
**System platform** file - defines the system hw with all of its components.

In Addition, it defines system power states.
"""
import json
import os
import sys
import tempfile
from typing import List

import networkx as nx
from graphviz import Digraph

from asap.strings import ATTRIBUTES, NAME_SEPARATOR

from .buses import Bus
from .hw import Clock, GlobalClock, HWComponent
from .ips import IP, Driver, Port
from .memories import Memory
from .states import HierarchyState, get_full_hw_name
from .strings import ComponentDesc, ResourceDesc, StateDesc

class Platform(HWComponent):
    """
    Platform contains all system components

    System components:
        * ips
        * buses
        * memories
        * clocks

    Platform creation:

    :param name: Platform name
    :param clocks: Clocks list
    :param ips: IPs list
    :param buses: Buses list
    :param memories: Memories list
    :param ips_connections: Tuples list of ips connections to the rest of platform [((ip, port), bus), ...]
    :param buses_connections: Tuples list of buses connections [(bus, bus)]
    :param memories_connections: Tuples list of memories connections [(bus, memory)]
    :param system_states: List of CStates ordered by the transition order

    Platform object provides API for sys modification, please see the following functions.
    """
    def __init__(self, name,
                 clocks: List[Clock] = None,
                 ips: List[IP] = None,
                 buses: List[Bus] = None,
                 memories: List[Memory] = None,
                 ips_connections=None,
                 buses_connections=None,
                 memories_connections=None,
                 system_states: List[HierarchyState] = None):
        super().__init__(name)
        self._clocks = clocks if clocks is not None else list()
        self._ips = ips if ips is not None else list()
        self._buses = buses if buses is not None else list()
        self._memories = memories if memories is not None else list()

        if ips_connections is not None:
            for (ip, p), bus in ips_connections:
                s_ip = self.get_ip(ip)
                if s_ip is None:
                    continue
                port = s_ip.get_port(p)
                dst_bus = self.get_bus(bus)
                if dst_bus is None or port is None:
                    continue
                self.connect_to_bus(port, dst_bus)

        if buses_connections is not None:
            for src_b, dst_b in buses_connections:
                src_bus = self.get_bus(src_b)
                dst_bus = self.get_bus(dst_b)
                if src_b is None or dst_b is None:
                    continue
                self.connect_to_bus(src_bus, dst_bus)

        if memories_connections is not None:
            for bus, mem in memories_connections:
                src_bus = self.get_bus(bus)
                memory = self.get_memory(mem)
                if src_bus is None or memory is None:
                    continue
                self.connect_to_memory(src_bus, memory)

        self._system_states = system_states if system_states is not None else list()
        self._system_states_exit_transitions = list()
        self._valid_graph = False
        self._graph = None

    # Clocks
    @property
    def clocks(self):
        """
        :return: List[Clocks] in platform
        """
        return self._clocks

    def create_clock(self, clock_name, period):
        """
        Create new clock and add it to platform.

        :param clock_name:
        :param period: us
        :return:

        Example::

            >>> p = Platform("new_platform")
            >>> p.create_clock("new_clock", 0.01)

        """
        clk = Clock(clock_name, period)
        self.add_clock(clk)

    def add_clock(self, clock: Clock):
        """
        Add new clock to platform

        :param clock: Clock object
        :return: Raise error if there is ip with same name in platform
        """
        for clk in self._clocks:
            if clk.name == clock.name:
                raise ValueError("Clock with same name: " + clock.name + " exists")
        self._clocks.append(clock)

    def add_clocks(self, clocks: List[Clock]):
        """
        Add clock lists to platform

        :param clocks: Clock objects list
        :return: Raise error if there is ip with same name in platform
        """
        for clock in clocks:
            self.add_clock(clock)

    def get_clock(self, clock_name):
        """
        Get clock by clock name

        :param clock_name:
        :return: Clock or None if did not find.
        """
        for clk in self._clocks:
            if clock_name == clk.name:
                return clk
        return None

    def del_clock(self, clock_name):
        """
        Delete clock from platform.

        :param clock_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for c in self._clocks:
            if c.name == clock_name:
                to_del = c
                break
        if not to_del:
            self._clocks.remove(to_del)
            return True
        return False

    @property
    def global_clock(self):
        """
        Getting platform global clock

        :return: Clock object
        """
        return GlobalClock.instance

    # IPs
    @property
    def ips(self):
        """
        :return: List[IPs] in platform.
        """
        return self._ips

    def add_ip(self, ip: IP):
        """
        Add new IP to platform

        :param ip: IP object
        :return: Raise error if there is ip with same name in platform.
        """
        for ip_ in self._ips:
            if ip_.name == ip.name:
                raise ValueError("IP with same name: " + ip.name + " exists")
        self._ips.append(ip)
        self._valid_graph = False

    def get_ip(self, ip_name):
        """
        Get IP by IP name

        :param ip_name:
        :return: IP or None if did not find.
        """
        for ip in self._ips:
            if ip_name == ip.name:
                return ip
        return None

    def is_ip_exist(self, ip_name):
        """
        Checks if IP exists in platform.

        :param ip_name:
        :return: True if found, False otherwise.
        """
        for ip in self._ips:
            if ip_name == ip.name:
                return True
        return False

    def del_ip(self, ip_name):
        """
        Delete IP from platform

        :param ip_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for ip in self._ips:
            if ip.name == ip_name:
                to_del = ip
                break
        if not to_del:
            self._ips.remove(to_del)
            return True
        return False

    def get_all_executing_units(self):
        """
        Getting all executing units of all ips.

        :return: Executing units list
        """
        return sum([ip.executing_units for ip in self._ips], [])

    def get_all_drivers(self):
        """
        Getting all drivers of all ips.

        :return: Drivers list
        """
        return sum([ip.drivers for ip in self._ips], [])

    # Buses
    @property
    def buses(self):
        """
        :return: List[Bus]
        """
        return self._buses

    def add_bus(self, bus: Bus):
        """
        Add new bus to platform

        :param bus: Bus object
        :return: Raise error if there is bus with same name in platform.
        """
        for bus_ in self._buses:
            if bus_.name == bus.name:
                raise ValueError("Bus with same name: " + bus.name + " exists")
        self._buses.append(bus)
        self._valid_graph = False

    def add_buses(self, buses: List[Bus]):
        """
        Adding buses list to platform

        :param buses: Bus objects list
        :return:
        """
        for bus in buses:
            self.add_bus(bus)

    def get_bus(self, bus_name):
        """
        Get bus by bus name

        :param bus_name:
        :return: Bus or None if did not find.
        """
        for bus in self._buses:
            if bus_name == bus.name:
                return bus
        return None

    def del_bus(self, bus_name):
        """
        Delete bus from platform

        :param bus_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for b in self._buses:
            if b.name == bus_name:
                to_del = b
                break
        if not to_del:
            self._buses.remove(to_del)
            return True
        return False

    # Memories
    @property
    def memories(self):
        """
        :return: List[Memory] in platform
        """
        return self._memories

    def add_memory(self, memory: Memory):
        """
        Add new memory to platform

        :param memory: Memory object
        :return: Raise error if there is memory with same name in platform.
        """
        for memory_ in self._memories:
            if memory_.name == memory.name:
                raise ValueError("Memory with same name: " + memory.name + " exists")
        self._memories.append(memory)
        self._valid_graph = False

    def add_memories(self, memories: List[Memory]):
        """
        Adding memories list to platform

        :param memories: Memory objects list
        :return:
        """
        for memory in memories:
            self.add_memory(memory)

    def get_memory(self, memory_name):
        """
        Get memory by name

        :param memory_name:
        :return: Memory or None if did not find.
        """
        for memory in self._memories:
            if memory_name == memory.name:
                return memory
        return None

    def del_memory(self, mem_name):
        """
        Delete memory from platform

        :param mem_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for mem in self._memories:
            if mem.name == mem_name:
                to_del = mem
                break
        if not to_del:
            self._memories.remove(to_del)
            return True
        return False

    def connect_to_bus(self, initiator, bus: Bus):
        """
        Connect to bus only - can be connected from Port/Bus.

        Added this level of validation so system will always be valid in terms of connections.

        :param initiator: Port/Bus objects
        :param bus: Bus object
        :return: Raise ValueError if failed
        """
        if bus not in self._buses:
            raise ValueError("Bus: " + bus.name + " is not part of this platform.")

        for initiator_ in bus.initiators:
            if initiator_.name == initiator.name:
                raise ValueError("Initiator: " + initiator_.name + " already connected to bus.")

        if isinstance(initiator, Port):
            if not initiator.ip:
                raise ValueError("Initiator of instance Port: " + initiator.name + " is not part of any ip.")
            bus.add_initiator(initiator)
            initiator.add_target(bus)
        elif isinstance(initiator, Bus):
            if initiator.name == bus.name:
                raise ValueError("Initiator of instance Bus: " + initiator.name + " can NOT connect to itself.")
            if not self.get_bus(initiator.name):
                raise ValueError("Initiator of instance Bus: " + initiator.name + " is not part of this platform.")
            bus.add_initiator(initiator)
            initiator.add_target(bus)
        else:
            raise ValueError("Initiator is neither bus neither port!")
        self._valid_graph = False

    def connect_to_memory(self, bus: Bus, memory: Memory):
        """
        Connect from bus only.

        Added this level of validation so system will be always be valid in terms of connections.

        :param bus:
        :param memory:
        :return: Raise ValueError if failed
        """
        if bus not in self._buses:
            raise ValueError("Bus: " + bus.name + " is not part of this platform.")

        if memory not in self._memories:
            raise ValueError("Memory: " + memory.name + " is not part of this platform.")

        for target in bus.targets:
            if target.name == memory.name:
                raise ValueError("Memory: " + memory.name + " already a target to this bus.")
        bus.add_target(memory)
        memory.add_initiator(bus)
        self._valid_graph = False

    @property
    def system_states(self):
        """
        :return: System states list.
        """
        return self._system_states

    @system_states.setter
    def system_states(self, system_states):
        """
        Setting system states

        :param system_states: [List]
        :return:
        """
        self._system_states = system_states

    def add_system_state(self, system_state):
        """
        Add new system state to system states list.

        :param system_state: System state HierarchyState
        :return: True if added, False else.
        """
        for state in self._system_states:
            if state.name == system_state.name:
                print('New System state', system_state.name, 'Already exists.')
                return False
        self._system_states.append(system_state)
        return True

    def get_system_state(self, system_state_name):
        """
        Returns the system state with the relevant name

        :param system_state_name:
        :return: SystemState or None if not found
        """
        for state in self._system_states:
            if state.name == system_state_name:
                return state
        return None

    def get_system_state_exit_transition(self, from_state, to_state):
        """
        Returns the matching StateTransition

        :param from_state: the name of the start state
        :param to_state: the name of the end state
        :return: StateTransition or None if not found
        """
        for exit_tr in self._system_states_exit_transitions:
            if exit_tr.from_state == from_state and exit_tr.to_state == to_state:
                return exit_tr
        return None

    @property
    def system_states_exit_transitions(self):
        """
        :return: system states exits transitions list
        """
        return self._system_states_exit_transitions

    @system_states_exit_transitions.setter
    def system_states_exit_transitions(self, value):
        """
        Setting system states exits transitions

        :param value:
        :return:
        """
        self._system_states_exit_transitions = value

    def add_system_state_exit_transition(self, _states_transition):
        """
        Adding a new system state exit transition

        :param _states_transition:
        :return:
        """
        for states_transition in self.system_states_exit_transitions:
            if states_transition.from_state == states_transition.from_state and \
                    states_transition.to_state == states_transition.to_state:
                states_transition.idle_time = _states_transition.idle_time
                return
        self._system_states_exit_transitions.append(_states_transition)

    def get_all_expressions(self):
        """
        :return: list of all expressions in system states and ip states
        """
        expressions = set()
        for system_state in self._system_states:
            expressions.add(system_state.expression)
        for ip in self.ips:
            for ip_state in ip.ip_states:
                expressions.add(ip_state.expression)
        for comp in self.get_all_drivers() + self.get_all_executing_units():
            for state in comp.constraints + comp.forces:
                expressions.add(state.expression)
        expressions = list(expressions)
        return expressions

    def get_all_constraints(self):
        """
        :return: list of all constraints in the platform
        """
        constraints = list()
        for dr in self.get_all_drivers():
            constraints = constraints + dr.constraints
        for ex_u in self.get_all_executing_units():
            constraints = constraints + ex_u.constraints
        for memory in self.memories:
            constraints = constraints + memory.constraints
        for bus in self.buses:
            constraints = constraints + bus.constraints
        return constraints

    def validate_platform(self):
        """
        Validating system platform:
            - Validate IP:
                - Drivers: has targets (Ports)
                - Ports: has initiators (Drivers) and targets (Buses)
            - Validate buses: all has initiators (Buses/Ports) and targets (Buses/Memories)
            - Validate memories: all memories has initiators only (Buses)
            - Validate ip and system states

        :return:
        """
        print("Validating System platform: " + self.name + "...")
        valid = True
        for ip in self._ips:
            valid &= self._validate_ip(ip)

        for bus in self._buses:
            valid &= self._validate_bus(bus)

        for memory in self._memories:
            valid &= self._validate_memory(memory)

        valid &= self._validate_system_and_ip_states()
        valid &= self._validate_forces_constraints()

        if not valid:
            print("System platform is NOT valid!")
            raise ValueError("System platform is not valid, please see error above.")
        print("System platform is valid!")

    def _validate_ip(self, ip: IP):
        valid = True
        for driver in ip.drivers:
            if not driver.targets:
                print("Driver: " + driver.name + " of IP: " + ip.name + " has no targets.")
                valid = False
            else:
                for target in driver.targets:
                    if not isinstance(target, Port):
                        print("Driver: " + driver.name + " of IP: " + ip.name + " has non port target:" +
                              target.name + ".")
                        valid = False
                    elif target not in ip.ports:
                        print("Driver: " + driver.name + " of IP: " + ip.name +
                              " is connected to port not part of this IP.")
                        valid = False
            if driver.initiators:
                print("Driver: " + driver.name + " of IP: " + ip.name + " has initiators.")
                valid = False

            if driver.clock not in self.clocks:
                print("Driver: " + driver.name + " of IP: " + ip.name + " clock is not part of the System")
                valid = False

        for port in ip.ports:
            if not port.initiators:
                print("Port: " + port.name + " of IP: " + ip.name + " has no initiators.")
                valid = False

            for initiator in port.initiators:
                if not isinstance(initiator, Driver):
                    print("Port: " + port.name + " of IP: " + ip.name + " has non driver initiator:" +
                          initiator.name + ".")
                    valid = False
                elif initiator not in ip.drivers:
                    print("Port: " + port.name + " of IP: " + ip.name +
                          " is connected to driver not part of this IP.")
                    valid = False

            if not port.targets:
                print("Port: " + port.name + " of IP: " + ip.name + " has no targets.")
                valid = False

            for target in port.targets:
                if not isinstance(target, Bus):
                    print("Port: " + port.name + " of IP: " + ip.name + " has non bus target:" +
                          target.name + ".")
                    valid = False
                elif target not in self._buses:
                    print("Port: " + port.name + " of IP: " + ip.name + " is connected to bus not part of this System.")
                    valid = False

        for exec_unit in ip.executing_units:
            if exec_unit.clock not in self.clocks:
                print("Executing Unit: " + exec_unit.name + " of IP: " + ip.name + " clock is not part of this System.")
                valid = False

        return valid

    def _validate_bus(self, bus: Bus):
        valid = True
        if not bus.initiators:
            print("Bus: " + bus.name + " has no initiators.")
            valid = False

        for initiator in bus.initiators:
            if not isinstance(initiator, Bus) and not isinstance(initiator, Port):
                print("Bus: " + bus.name + " has non port or bus initiator:" + initiator.name + ".")
                valid = False
            elif isinstance(initiator, Bus) and initiator not in self._buses:
                print("Bus: " + bus.name + " is connected to bus not part of this system: " + initiator.name)
                valid = False
            elif isinstance(initiator, Port) and initiator.ip is not None and initiator.ip not in self._ips:
                print("Bus: " + bus.name + " is connected to port of ip not part of this System: " + initiator.name +
                      " - " + initiator.ip.name)
                valid = False
        if not bus.targets:
            print("Bus: " + bus.name + " has no targets.")
            valid = False

        for target in bus.targets:
            if not isinstance(target, Bus) and not isinstance(target, Memory):
                print("Bus: " + bus.name + " has non bus or memory target:" + target.name + ".")
                valid = False

        if bus.clock not in self.clocks:
            print("Bus: " + bus.name + "'s clock is not part of this System.")
            valid = False
        return valid

    def _validate_memory(self, memory: Memory):
        valid = True
        if not memory.initiators:
            print("Memory: " + memory.name + " has no initiators.")
            valid = False

        if len(memory.initiators) != 1:
            print("Memory: " + memory.name + " should have 1 initiator only. Found " +
                  str(len(memory.initiators)) + " initiators")
            valid = False
        for initiator in memory.initiators:
            if not isinstance(initiator, Bus):
                print("Memory: " + memory.name + " has a non bus initiator:" + initiator.name + ".")
                valid = False
            elif initiator not in self._buses:
                print("Memory: " + memory.name + " is connected to bus not part of this System.")
                valid = False

        if memory.targets:
            print("Memory: " + memory.name + " has targets.")
            valid = False

        if memory.clock not in self.clocks:
            print("Memory: " + memory.name + "'s clock is not part of this System.")
            valid = False
        return valid

    def _validate_system_and_ip_states(self):
        valid = True
        already_read_expressions = list()
        for expression in self.get_all_expressions():
            for read_expression in already_read_expressions:
                if expression.name == read_expression.name:
                    print("There are two different expressions with the same name: " + expression.name)
                    valid = False
            already_read_expressions.append(expression)
        return valid

    def _validate_forces_constraints(self):
        valid = True
        for dr in self.get_all_drivers():
            valid &= Platform._validate_forces_constraints_per_component(dr)
        for ex_u in self.get_all_executing_units():
            valid &= Platform._validate_forces_constraints_per_component(ex_u)
        for memory in self.memories:
            valid &= Platform._validate_forces_constraints_per_component(memory)
        for bus in self.buses:
            valid &= Platform._validate_forces_constraints_per_component(bus)
        return valid

    @staticmethod
    def _validate_forces_constraints_per_component(hw):
        valid = True
        state_names = [state.name for state in hw.power_states + [hw.active_state]]
        for force in hw.forces:
            if force.name not in state_names:
                print("There isn't a state called " + force.name + " in " + hw.name)
                valid = False
        for constraint in hw.constraints:
            if constraint.name not in state_names:
                print("There isn't a state called " + constraint.name + " in " + hw.name)
                valid = False
        return valid

    def to_graph(self):
        if self._valid_graph:
            return self._graph

        if not self._graph:
            self._graph = nx.DiGraph()
        else:
            self._graph.clear()
        for ip in self._ips:
            self._graph.add_node((ip.name, ResourceDesc.IP))

        for bus in self._buses:
            self._graph.add_node((bus.name, ResourceDesc.BUS))

        for memory in self._memories:
            self._graph.add_node((memory.name, ResourceDesc.MEMORY))

        for memory in self._memories:
            for initiator in memory.initiators:
                self._graph.add_edge((initiator.name, ResourceDesc.BUS), (memory.name, ResourceDesc.MEMORY))

        for bus in self._buses:
            for initiator in bus.initiators:
                if isinstance(initiator, Bus):
                    self._graph.add_edge((initiator.name, ResourceDesc.BUS), (bus.name, ResourceDesc.BUS))
                else:
                    self._graph.add_edge((initiator.ip.name, ResourceDesc.IP), (bus.name, ResourceDesc.BUS))
        return self._graph

    def get_routing_path(self, initiator, target):
        """
        Return list of routing tuples in order (name, type)...

        :param initiator: can be port/bus
        :param target: can be bus/memory
        :return:
        """

        if isinstance(initiator, IP):
            initiator_type = ResourceDesc.IP
        elif isinstance(initiator, Port):
            initiator_type = ResourceDesc.IP
            initiator = initiator.ip
        elif isinstance(initiator, Bus):
            initiator_type = ResourceDesc.BUS
        else:
            raise ValueError("Initiator is neither bus neither port!")

        if isinstance(target, Bus):
            target_type = ResourceDesc.BUS
        elif isinstance(target, Memory):
            target_type = ResourceDesc.MEMORY
        else:
            raise ValueError("Target is neither bus neither port!")

        self.to_graph()
        path = nx.shortest_path(self._graph, source=(initiator.name, initiator_type),
                                target=(target.name, target_type))
        return path

    def get_all_paths(self, initiator, target):
        """
        Return list of list of routing tuples in order (name, type)...

        :param initiator: can be ip/port/bus
        :param target: can be bus/memory
        :return:
        """
        if isinstance(initiator, IP):
            initiator_type = ResourceDesc.IP
        elif isinstance(initiator, Port):
            initiator_type = ResourceDesc.IP
            initiator = initiator.ip
        elif isinstance(initiator, Bus):
            initiator_type = ResourceDesc.BUS
        else:
            raise ValueError("Initiator is neither bus neither port!")

        if isinstance(target, Bus):
            target_type = ResourceDesc.BUS
        elif isinstance(target, Memory):
            target_type = ResourceDesc.MEMORY
        else:
            raise ValueError("Target is neither bus neither port!")

        self.to_graph()
        return nx.all_simple_paths(self._graph, source=(initiator.name, initiator_type),
                                   target=(target.name, target_type))

    def draw(self, file_name, view=False, format_="svg", keep_gv=False):
        """
        Drawing system platform

        :param file_name:
        :param view:
        :param format_:
        :param keep_gv:
        :return: rendered file name
        """
        graph = Digraph(self._name, format=format_)

        graph.attr('graph', splines='ortho')
        for ip in self._ips:
            ex_names = ' '
            for ex in ip.executing_units:
                ex_names += ex.name + ' '
            driver_names = ' '
            for driver in ip.drivers:
                driver_names += driver.name + ' '
            graph.node(ip.name, label=ip.name, shape="square", color="blue", style="setlinewidth(2)",
                       tooltip='ex units: ' + str([ex.name for ex in ip.executing_units]) + '\n' +
                               'drivers: ' + str([dr.name for dr in ip.drivers]) + '\n' + 'clock: ' +
                               ip.clock.name + ' (period: ' + str(ip.clock.period) + 'us)')

        for bus in self._buses:
            graph.node(bus.name, label=bus.name, shape="rectangle", color="green", style="setlinewidth(2)", id=bus.name,
                       tooltip='bus width: ' + str(bus.bus_width) + 'B' + '\n' + 'clock: ' + bus.clock.name
                               + ' (period: ' + str(bus.clock.period) + 'us)')

        for mem in self._memories:
            graph.node(mem.name, label=mem.name, shape="house", color="red", style="setlinewidth(2)", id=mem.name,
                       tooltip='size: ' + str(mem.size) + 'B' + '\n' + 'clock: ' + mem.clock.name
                               + ' (period: ' + str(mem.clock.period) + 'us)')

        for memory in self._memories:
            for initiator in memory.initiators:
                graph.edge(initiator.name, memory.name, arrowhead='vee')

        for bus in self._buses:
            for initiator in bus.initiators:
                if isinstance(initiator, Bus):
                    graph.edge(initiator.name, bus.name, arrowhead='vee')
                else:
                    graph.edge(initiator.ip.name, bus.name, arrowhead='vee')

        if file_name.endswith("." + format_):
            file_name, file_extension = os.path.splitext(file_name)
        graph.render(file_name, view=view)
        if not keep_gv:
            try:
                os.remove(file_name)
            except OSError:
                pass

        render_file_name = file_name + '.' + str(format_)
        return render_file_name

    def _repr_html_(self):
        """
        Jupyter integration. This will be called by Jupyter to display the object.

        :return: html code
        """
        fd, tmp_file = tempfile.mkstemp(".svg")
        os.close(fd)
        self.draw(tmp_file, format_='svg', view=False)
        with open(tmp_file, 'r') as stream:
            text = stream.read()
        os.unlink(tmp_file)
        return text

    def reset(self):
        """
        Resetting platform
            - resetting buses: reset active initiators and targets to none.

        :return:
        """
        for bus in self.buses:
            bus.reset()

    def to_dict(self):
        """
        Converting system platform to dictionary

        :return: Dictionary
        """
        desc = super().to_dict()
        desc[self.name][ComponentDesc.CLOCKS] = list()
        desc[self.name][ComponentDesc.IPS] = list()
        desc[self.name][ComponentDesc.BUSES] = list()
        desc[self.name][ComponentDesc.MEMORIES] = list()
        desc[self.name][StateDesc.SYSTEM_STATES] = list()
        for clock in self.clocks:
            desc[self.name][ComponentDesc.CLOCKS].append(clock.to_dict())
        for ip in self.ips:
            desc[self.name][ComponentDesc.IPS].append(ip.to_dict())
        for bus in self.buses:
            desc[self.name][ComponentDesc.BUSES].append(bus.to_dict())
        for memory in self.memories:
            desc[self.name][ComponentDesc.MEMORIES].append(memory.to_dict())
        for state in self._system_states:
            desc[self.name][StateDesc.SYSTEM_STATES].append(state.to_dict())
        return desc

    def save(self, filename):
        """
        Saving platform into a json file.

        :param filename:
        :return:
        """
        _format = 'json'
        f, ext = os.path.splitext(filename)
        if ext != _format:
            filename = f + '.' + _format
        file = open(filename, 'w')
        json.dump(self.to_dict(), file)
        file.close()

    @staticmethod
    def load(desc):
        """
        Creates a new system from system dictionary representation

        :param desc: dict that represents a system in the following way
                    {<name>: {'Clocks': <clock_list>,
                    'Ips': <ip_list>, 'Ports': <port_list>, 'Executing units: <eu_list>}}
        :return: Platform
        """
        name = list(desc.keys())[0]
        system = Platform(name)

        # Adding clocks
        try:
            clocks = list()
            for clock_desc in desc[name][ComponentDesc.CLOCKS]:
                clock = Clock.load(clock_desc)
                system.add_clock(clock)
                clocks.append(clock)
        except KeyError:
            raise ValueError("Failed to load clocks: the structure of the file isn't supported")

        # Adding buses
        try:
            for bus_desc in desc[name][ComponentDesc.BUSES]:
                bus = Bus.load(bus_desc, clocks)
                system.add_bus(bus)
        except KeyError:
            raise ValueError("Failed to load buses: the structure of the file isn't supported")

        # Adding memories and connects them to the relevant buses
        try:
            for memory_desc in desc[name][ComponentDesc.MEMORIES]:
                memory = Memory.load(memory_desc, clocks)
                system.add_memory(memory)
                for memory_repr in memory_desc.values():
                    for initiator_desc in memory_repr[ComponentDesc.INITIATORS]:
                        bus = system.get_bus(initiator_desc[ComponentDesc.NAME])
                        system.connect_to_memory(bus, memory)
        except KeyError:
            raise ValueError("Failed to load memories: the structure of the file isn't supported")

        # Adding ips
        try:
            for ip_desc in desc[name][ComponentDesc.IPS]:
                ip = IP.load(ip_desc, clocks)
                system.add_ip(ip)
        except KeyError:
            raise ValueError("Failed to load IPs: the structure of the file isn't supported")

        # Connecting buses to buses and buses to ip ports
        ips = system.ips
        try:
            for bus_desc in desc[name][ComponentDesc.BUSES]:
                for bus_name, bus_repr in bus_desc.items():
                    bus = system.get_bus(bus_name)
                    for initiator_desc in bus_repr[ComponentDesc.INITIATORS]:
                        if initiator_desc[ComponentDesc.TYPE] == ResourceDesc.PORT:
                            for ip in ips:
                                port = ip.get_port(initiator_desc[ComponentDesc.NAME])
                                if port is not None:
                                    system.connect_to_bus(port, bus)
                                    break

                        elif initiator_desc[ComponentDesc.TYPE] == ResourceDesc.BUS:
                            initiator_bus = system.get_bus(initiator_desc[ComponentDesc.NAME])
                            system.connect_to_bus(initiator_bus, bus)

                        else:
                            raise ValueError("Failed to connect bus: "
                                             "the type of the initiator of the bus isn't supported")
        except KeyError:
            raise ValueError("Failed to load buses: the structure of the file isn't supported")

        # Adding system states
        try:
            system_states = list()
            for state_desc in desc[name].get(StateDesc.SYSTEM_STATES, list()):
                system_states.append(HierarchyState.load(state_desc))
            system.system_states = system_states
        except KeyError:
            raise ValueError("Failed to load system states: the structure of the file isn't supported")

        # Adding custom attributes
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            system.attach_attribute(attr, value)

        return system

    def upload(self, attributes=None):
        pass

    @staticmethod
    def download(name):
        """
        Downloads the platform from conduit by name

        :param name: name of the item in conduit
        :return: Platform
        """
        return None

    def dump_power_connectivity_file(self, output_dir):
        """
        Dumps template power csv file with platform power states, in addition, dumps connectivity file.

        :param output_dir: Directory to dump power and connectivity file to
        :return: <Platform name>_power_states.csv and <Platform name>_connectivity.csv in output directory
        """
        with open(os.path.join(output_dir, self.name + '_power_states.csv'), 'w', newline='') as power_states_fd:
            self._write_power_states(power_states_fd, 'CORES', self.get_all_executing_units())
            self._write_power_states(power_states_fd, 'INTERFACES', self.get_all_drivers())
            self._write_power_states(power_states_fd, 'BUSES', self.buses)
            self._write_power_states(power_states_fd, 'MEMORIES', self.memories)
            power_states_fd.write('EXPRESSIONS_START\n')
            self._write_expressions(power_states_fd, self.get_all_expressions())
            power_states_fd.write('EXPRESSIONS_END\n')
            power_states_fd.write('CONSTRAINTS_START\n')
            self._write_constraints(power_states_fd)
            power_states_fd.write('CONSTRAINTS_END\n')
            power_states_fd.write('FORCES_START\n')
            self._write_forces(power_states_fd)
            power_states_fd.write('FORCES_END\n')
            power_states_fd.write('IP_STATE_TRANSITIONS_START\n')
            self._write_ip_states(power_states_fd, self.ips)
            power_states_fd.write('STATE_TRANSITIONS_END\n')
            power_states_fd.write('SYSTEM_STATE_TRANSITIONS_START\n')
            power_states_fd.write('source,name,idle_time,expression\n')
            self._write_system_states(power_states_fd, self.system_states)
            power_states_fd.write('STATE_TRANSITIONS_END\n')
            power_states_fd.write('SYSTEM_STATE_EXIT_LATENCY\n')
            power_states_fd.write('source,name,idle_time,expression\n')
            self._write_system_states_exit_transitions(power_states_fd, self.system_states_exit_transitions)
            power_states_fd.write('STATE_TRANSITIONS_END\n')
            power_states_fd.write('EXTRA_PROPERTIES\n')
            power_states_fd.write('name,value\n')
            power_states_fd.write('EXTRA_PROPERTIES_END')

        with open(os.path.join(output_dir, self.name + '_connectivity.csv'), 'w', newline='') as connectivity_file:
            for clk in self.clocks:
                connectivity_file.write('clock, ' + clk.name + ',' + str(int(clk.period * 1000)) + '\n')
            self._write_clock_connectivity(connectivity_file, 'core', self.get_all_executing_units(), True)
            self._write_clock_connectivity(connectivity_file, 'driver', self.get_all_drivers(), True)
            self._write_clock_connectivity(connectivity_file, 'bus', self.buses)
            self._write_clock_connectivity(connectivity_file, 'memory', self.memories)

            for dr in self.get_all_drivers():
                paths = set()
                for mem in self.memories:
                    for path in self.get_all_paths(dr.ip, mem):
                        for elem in path[1:]:
                            paths.add(elem[0])
                connectivity_file.write('driver_ptm,' + dr.ip.name + NAME_SEPARATOR + dr.name + ',' + ' '.join(paths)
                                        + '\n')
            for ip in self.ips:
                connectivity_file.write('hierarchy,' + ip.name)

    @staticmethod
    def _write_power_states(ps_writer, title, resources):
        ps_writer.write(title + '_START\n')
        for r in resources:
            name = get_full_hw_name(r)
            ps_writer.write(name + '\n')
            ps_writer.write('name,reference_voltage,reference_frequency,reference_dynamic_power,'
                            'reference_leakage_power,active_state_name,module_type,system_dependency\n')
            ps_writer.write(name + ',' + str(r.active_state.reference_voltage) + ','
                            + str(r.active_state.reference_frequency) + ','
                            + str(r.active_state.reference_dynamic_power) + ','
                            + str(r.active_state.reference_leakage_power) + ','
                            + str(r.active_state.name) + ','
                            + 'def' + ',' + r.active_state.system_dependency + '\n')
            ps_writer.write('power states\n')
            ps_writer.write('name,reference_leakage_power,reference_voltage,entrance_latency_in_us,'
                            'exit_latency_in_us,trigger_in_us\n')
            for power_state in r.power_states:
                ps_writer.write(power_state.name + ',' + str(power_state.reference_leakage_power) + ','
                                + str(power_state.reference_voltage) + ',' + str(power_state.entrance_latency) + ','
                                + str(power_state.exit_latency) + ',' + str(power_state.trigger) + '\n')
            ps_writer.write('\n')
        ps_writer.write(title + '_END\n')

    @staticmethod
    def _write_expressions(ps_writer, expressions):
        for expression in expressions:
            ps_writer.write(expression.name + '\n')
            for condition in expression.conditions:
                ps_writer.write(condition.hw_component + ',' + condition.condition + ',' +
                                condition.state_name + ',1,' + str(condition.negate).lower() + '\n')
            ps_writer.write('END\n')

    def _write_constraints(self, ps_writer):
        ps_writer.write('module_name,state_name,expression_name\n')
        for dr in self.get_all_drivers():
            for constraint in dr.constraints:
                ps_writer.write(get_full_hw_name(dr) + ',' + constraint.name + ',' + constraint.expression.name + '\n')
        for ex_u in self.get_all_executing_units():
            for constraint in ex_u.constraints:
                ps_writer.write(get_full_hw_name(ex_u) + ',' + constraint.name + ',' +
                                constraint.expression.name + '\n')
        for memory in self.memories:
            for constraint in memory.constraints:
                ps_writer.write(get_full_hw_name(memory) + ',' + constraint.name + ','
                                + constraint.expression.name + '\n')
        for bus in self.buses:
            for constraint in bus.constraints:
                ps_writer.write(get_full_hw_name(bus) + ',' + constraint.name + ',' + constraint.expression.name + '\n')

    def _write_forces(self, ps_writer):
        ps_writer.write('module_name,state_name,expression_name,application_period\n')
        for dr in self.get_all_drivers():
            for force in dr.forces:
                ps_writer.write(get_full_hw_name(dr) + ',' + force.name + ',' + force.expression.name + ',' + '\n')
        for ex_u in self.get_all_executing_units():
            for force in ex_u.forces:
                ps_writer.write(get_full_hw_name(ex_u) + ',' + force.name + ',' + force.expression.name + ',' + '\n')
        for memory in self.memories:
            for force in memory.forces:
                ps_writer.write(get_full_hw_name(memory) + ',' + force.name + ',' + force.expression.name + ',' + '\n')
        for bus in self.buses:
            for force in bus.forces:
                ps_writer.write(get_full_hw_name(bus) + ',' + force.name + ',' + force.expression.name + ',' + '\n')

    @staticmethod
    def _write_ip_states(ps_writer, ips):
        for ip in ips:
            if ip.ip_states:
                ps_writer.write(ip.name + '\n')
                ps_writer.write('name,dynamic_power,leakage_power,expression,delay\n')
                ps_writer.write('default,0,0,DEFAULT,0\n')
                for state in ip.ip_states:
                    ps_writer.write(state.name + ',0,0,' + state.expression.name + ',' + str(state.idle_time) + '\n')
                ps_writer.write('END\n')

    @staticmethod
    def _write_system_states(ps_writer, states):
        ps_writer.write('ANY,default,0,DEFAULT\n')
        prev = 'default'
        for state in states:
            ps_writer.write(prev + ',' + state.name + ',' + str(state.idle_time) + ',' + state.expression.name + '\n')
            prev = state.name

    @staticmethod
    def _write_system_states_exit_transitions(ps_writer, states):
        for state in states:
            ps_writer.write(state.from_state + ',' + state.to_state + ',' + str(state.idle_time) + ',DEFAULT\n')

    @staticmethod
    def _write_clock_connectivity(con_writer, hw_type, resources, concatenate_father=False):
        for r in resources:
            if concatenate_father:
                name = r.ip.name + NAME_SEPARATOR + r.name
            else:
                name = r.name
            con_writer.write(hw_type + ',' + name + ',' + r.clock.name + '\n')
