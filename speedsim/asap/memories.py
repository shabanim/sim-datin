"""
**Memories** definition. Any new memory should be defined in here.

"""
from .hw import Clock, GeneralHWComponent, TickingHWComponent
from .states import ActiveState, HierarchyState
from .strings import ATTRIBUTES, ComponentDesc, ResourceDesc, StateDesc


class Memory(GeneralHWComponent):
    """
    Memory component - has no targets. must have initiator (bus).

    Defaults:
        - Bus width = 64Byte
        - Latency = 0.01us

    :param name: clock name
    :param clock: Clock
    :param size: size in KB
    :param bus_width: memory bus width
    :param latency: transition latency in us
    :param power_states: list of PowerStates by order
    :param forces: list of Forces
    :param constraints: list of Constraints
    """
    DEFAULT_BW = 64  # Byte
    DEFAULT_LATENCY = 0.01  # us

    def __init__(self, name, clock: Clock, size: int, bus_width: int = DEFAULT_BW, latency: float = DEFAULT_LATENCY,
                 power_states=None, active_state=None, forces=None, constraints=None):
        super(Memory, self).__init__(name=name, clock=clock, _type=ResourceDesc.MEMORY, power_states=power_states,
                                     active_state=active_state, forces=forces, constraints=constraints)
        self._size = size
        self._bus_width = bus_width
        self._latency = latency

    @property
    def size(self):
        """
        :return: Memory size (Int)
        """
        return self._size

    @size.setter
    def size(self, size):
        """
        :param size: Int num
        :return:
        """
        self._size = size

    @property
    def bus_width(self):
        """
        :return: Bus width in bytes
        """
        return self._bus_width

    @bus_width.setter
    def bus_width(self, bus_width):
        """
        :param bus_width: In bytes
        :return:
        """
        self._bus_width = bus_width

    @property
    def latency(self):
        return self._latency

    @latency.setter
    def latency(self, latency):
        self._latency = latency

    def add_initiator(self, bus):
        """
        Memory may have only 1 initiator of type Bus.

        :param bus: Bus object
        :return:
        """
        self._initiators = list()
        super().add_initiator(bus)

    # Overriding parent add_target function so it can't be initiator to any.
    def add_target(self, target):
        return None

    @property
    def bw(self):
        """
        Memory BW is bus_width/clock

        :return: BW in Bytes/Cycles
        """
        return self._bus_width/self.clock.period

    def to_dict(self):
        desc = super().to_dict()
        desc[self._name][ComponentDesc.SIZE] = self._size
        desc[self._name][ComponentDesc.BUS_WIDTH] = self._bus_width
        desc[self._name][ComponentDesc.LATENCY] = self._latency
        return desc

    @staticmethod
    def load(desc, clocks):
        """
        Creates a new memory from a memory dictionary representation

        :param desc: a dict representing a memory {<name>: {'Clock': <clock_name>, 'Initiators': <list>,
                            'Targets': <list>, 'Size': <number>, 'Bus Width': <number>, 'Latency': <number>}}
        :param clocks: list of clocks
        :return: Memory
        """
        name = list(desc.keys())[0]
        clk = None
        for clock in clocks:
            if clock.name == desc[name][ComponentDesc.CLOCK]:
                clk = clock
                break
        if clk is None:
            raise ValueError('Clock: ', desc[name][ComponentDesc.CLOCK], ' in memory', name, 'does not exist!.')
        memory = Memory(name, clk, desc[name][ComponentDesc.SIZE],
                        desc[name].get(ComponentDesc.BUS_WIDTH, Memory.DEFAULT_BW),
                        desc[name].get(ComponentDesc.LATENCY, Memory.DEFAULT_LATENCY),
                        power_states=TickingHWComponent.load_power_states(desc[name].get(StateDesc.POWER_STATES)),
                        active_state=ActiveState.load(desc[name].get(StateDesc.ACTIVE_STATE)),
                        forces=[HierarchyState.load(force) for force in desc[name].get(StateDesc.FORCES, list())],
                        constraints=[HierarchyState.load(constraint) for constraint in
                                     desc[name].get(StateDesc.CONSTRAINTS, list())])
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            memory.attach_attribute(attr, value)
        return memory
