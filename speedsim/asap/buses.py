"""
**Buses** definition. Any new bus should be implemented here.
    - Basic bus: aware of active initiators/targets, exposes bw function to be overwritten for bw calculation.
"""
from collections import Counter
from enum import Enum

from .hw import Clock, GeneralHWComponent, TickingHWComponent
from .states import ActiveState, HierarchyState
from .strings import ATTRIBUTES, ComponentDesc, ResourceDesc, StateDesc


class ArbitrationScheme(Enum):
    """
    Buses arbitration schemes:
        * FIXED
        * PRIORITY
        * ROUND ROBIN
    """
    FIXED = "FIXED"
    PRIORITY = "PRIORITY"
    ROUND_ROBIN = "ROUND_ROBIN"


class Bus(GeneralHWComponent):
    """
    BUS Component, may have multiple initiators and targets.

    Bus implements default BW calculation function where it divides BW between all initiators equally.

    Bus is aware of active initiators and active targets. Helps for calculating BW.

    Defaults:
        - Bus width = 64Byte
        - Latency = 0.01us

    :param name: Bus name
    :param clock: Clock
    :param bus_width: In bytes, default is 64B
    :param latency: Transition latency in us
    :param arb: Bus arbitration scheme

    """
    DEFAULT_BW = 64  # Byte
    DEFAULT_LATENCY = 0.01  # us

    def __init__(self, name, clock: Clock, bus_width: int = DEFAULT_BW, latency: float = DEFAULT_LATENCY,
                 arb: ArbitrationScheme = ArbitrationScheme.FIXED, power_states=None, active_state=None,
                 forces=None, constraints=None):

        super(Bus, self).__init__(name=name, clock=clock, _type=ResourceDesc.BUS, power_states=power_states,
                                  active_state=active_state, forces=forces, constraints=constraints)
        self._bus_width = bus_width
        self._arb_scheme = arb
        self._active_initiators = Counter()  # represents the active initiators and how many times initiated
        self._active_targets = Counter()
        self._bus_load = dict()  # dict that represents the actual bus load from the initaitors
        self._latency = latency
        self._bw_func = self.default_bw_func

    @property
    def bus_width(self):
        """
        :return: Bus width in Bytes
        """
        return self._bus_width

    @bus_width.setter
    def bus_width(self, bus_width: int):
        """
        :param bus_width: In bytes
        :return:
        """
        self._bus_width = bus_width

    @property
    def arbitration_scheme(self):
        """
        :return: Arbitration scheme
        """
        return self._arb_scheme

    @arbitration_scheme.setter
    def arbitration_scheme(self, arb_scheme: ArbitrationScheme):
        """
        :param arb_scheme: One of defined arbitration scheme
        :return:
        """
        self._arb_scheme = arb_scheme

    @property
    def latency(self):
        return self._latency

    @latency.setter
    def latency(self, latency):
        self._latency = latency

    @property
    def active_initiators(self):
        """
        :return: Currently active initiators of the bus
        """
        return self._active_initiators

    @property
    def bus_load(self):
        """
        dict that represents the actual bus load from the initiators

        :return: dict (initiator -> load)
        """
        return self._bus_load

    def set_bw_func(self, bw_func):
        """
        Override bus BW function, bw_func should take bus as input and return BW in Bytes/Cycles.

        :param bw_func: function pointer
        :return:
        """
        self._bw_func = bw_func

    @staticmethod
    def default_bw_func(bus):
        """
        Default BW function implementation, divides BW between all active initiators.

        :param bus: Bus object
        :return: bandwidth
        """
        bw = bus.bus_width/bus.clock.period
        if len(bus.active_initiators.keys()) == 0:
            return bw
        return bw/len(bus.active_initiators.keys())

    @staticmethod
    def load_bw_func(bus):
        """
        Load BW function implementation, calculated bw according to each initiator load

        :param bus: Bus object
        :return: bandwidth
        """
        bw = bus.bus_width/bus.clock.period
        bus_load = sum(bus.bus_load.values()) if len(bus.bus_load.values()) > 0 else 0
        if bus_load < 1:
            return bw
        return bw/bus_load

    @staticmethod
    def naive_bw_func(bus):
        """
        Most Naive BW function, bus_width/clock.period

        :param bus: Bus Object
        :return:
        """
        return bus.bus_width/bus.clock.period

    @property
    def bw(self):
        """
        Calling BW function with self.

        :return: BW in Bytes/Cycles
        """
        return self._bw_func(self)

    @property
    def out_bw(self):
        return self.bus_width / self.clock.period

    def reset(self):
        """
        Resetting bus, clear active initiators and targets

        :return:
        """
        self._active_initiators = Counter()
        self._active_targets = Counter()
        self._bus_load = dict()

    def to_dict(self):
        desc = super().to_dict()
        desc[self._name][ComponentDesc.BUS_WIDTH] = self._bus_width
        desc[self._name][ComponentDesc.LATENCY] = self._latency
        return desc

    @staticmethod
    def load(desc, clocks):
        """
        Creates a new bus from a bus dictionary representation

        :param desc: a dict representing a bus {<name>: {'Clock': <clock_name>, 'Initiators': <list>,
                    'Targets': <list>, 'Bus Width': <number>, 'Latency': <number>}}
        :param clocks: list of clocks
        :return: Bus
        """
        name = list(desc.keys())[0]
        clk = None
        for clock in clocks:
            if clock.name == desc[name][ComponentDesc.CLOCK]:
                clk = clock
                break
        if clk is None:
            raise ValueError('Clock: ', desc[name][ComponentDesc.CLOCK], ' in bus ', name, 'does not exist!.')
        bus = Bus(name, clk, desc[name].get(ComponentDesc.BUS_WIDTH, Bus.DEFAULT_BW),
                  desc[name].get(ComponentDesc.LATENCY, Bus.DEFAULT_LATENCY),
                  power_states=TickingHWComponent.load_power_states(desc[name].get(StateDesc.POWER_STATES)),
                  active_state=ActiveState.load(desc[name].get(StateDesc.ACTIVE_STATE)),
                  forces=[HierarchyState.load(force) for force in desc[name].get(StateDesc.FORCES, list())],
                  constraints=[HierarchyState.load(constraint) for constraint in
                               desc[name].get(StateDesc.CONSTRAINTS, list())])
        for attr, value in desc[name].get(ATTRIBUTES, dict()).items():
            bus.attach_attribute(attr, value)
        return bus
