"""
Definition of Basic HW components.
"""
from collections import defaultdict
from enum import Enum

from .states import ActiveState, PowerState
from .strings import ATTRIBUTES, ComponentDesc, ResourceDesc, StateDesc

GLOBAL_CLOCK_NAME = "__GLOBAL_CLOCK__"
GLOBAL_CLOCK_PERIOD_US = 0.01


class ComponentState(Enum):
    """
    Component state: currently component can be Free/Busy
    """
    BUSY = "BUSY"
    FREE = "FREE"


class HWComponent:
    """
    Primitive Hardware component - dynamic attributes.
    """
    def __init__(self, name, _type=ResourceDesc.HW_COMPONENT):
        self._name = name
        self._state = ComponentState.FREE
        self._type = _type
        self._attributes = dict()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, _state):
        self._state = _state

    @property
    def type(self):
        return self._type

    def attach_attribute(self, attribute, value):
        self._attributes[attribute] = value

    def get_attribute(self, attribute, default=None):
        return self._attributes.get(attribute, default)

    def to_dict(self):
        """
        Converting component to dictionary {attr: value}

        :return: Dictionary
        """
        desc = {self.name: dict()}
        desc[self.name][ATTRIBUTES] = dict()
        for attr, value in self._attributes.items():
            if self._is_attribute_valid(value):
                desc[self.name][ATTRIBUTES][attr] = value
        return desc

    @staticmethod
    def _is_attribute_valid(attribute):
        """
        Checks if a attribute contains basic classes, including inside lists and dictionaries

        :param attribute: the attribute to check
        :return: bool
        """
        valid = True
        if isinstance(attribute, list):
            for item in attribute:
                valid = valid and HWComponent._is_attribute_valid(item)
        elif isinstance(attribute, dict):
            for val in attribute.values():
                valid = valid and HWComponent._is_attribute_valid(val)
        else:
            return type(attribute).__name__ in ['str', 'int', 'float', 'bool']
        return valid


class Clock(HWComponent):
    """
    Clock component. Defined by period in us.

    :param name: clock name
    :param period: period in us
    """
    def __init__(self, name, period: float):
        super().__init__(name, ResourceDesc.CLOCK)
        self._period = period

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, period: float):
        self._period = period

    def to_dict(self):
        desc = super().to_dict()
        desc[self._name].update({ComponentDesc.PERIOD: self._period})
        return desc

    @staticmethod
    def load(desc):
        """
        Creates a new clock from a clock dictionary representation

        :param desc: a dict representing a clock {<name>: {'Period': <period>}}
        :return: Clock
        """
        name = list(desc.keys())[0]
        if name == ComponentDesc.GLOBAL_CLOCK:
            return GlobalClock(name, desc[name][ComponentDesc.PERIOD]).instance
        else:
            return Clock(name, desc[name][ComponentDesc.PERIOD])


class TickingHWComponent(HWComponent):
    """
    Hardware component with a clock. If no clock defined, then system global clock will be used.
    """
    def __init__(self, clock: Clock, power_states=None, active_state=None, forces=None, constraints=None, **kwargs):
        super(TickingHWComponent, self).__init__(**kwargs)
        self._clock = clock
        self._power_states = [PowerState()] if power_states is None else power_states
        self._active_state = ActiveState() if active_state is None else active_state
        self._forces = forces if forces is not None else list()
        self._constraints = constraints if forces is not None else list()

    @property
    def clock(self):
        """
        :return: Clock
        """
        if not self._clock:
            return GlobalClock.instance
        return self._clock

    @clock.setter
    def clock(self, clock: Clock):
        """
        Setting connected clock

        :param clock:
        :return:
        """
        self._clock = clock

    @property
    def power_states(self):
        """
        :return: Power states list
        """
        return self._power_states

    @power_states.setter
    def power_states(self, power_states):
        """
        Setting power states

        :param power_states:
        :return:
        """
        self._power_states = power_states

    def add_power_state(self, power_state):
        """
        Add new power states to power states list

        :param power_state:
        :return:
        """
        for state in self._power_states:
            if state.name == power_state.name:
                print('New Power state', power_state.name, 'Already exists.')
                return
        self._power_states.append(power_state)

    def get_power_state(self, state_name):
        """
        Returns the matching power state

        :param state_name: state name
        :return: State
        """
        for state in self._power_states:
            if state.name == state_name:
                return state
        return None

    @property
    def active_state(self):
        """
        :return: Active state
        """
        return self._active_state

    @active_state.setter
    def active_state(self, active_state):
        """
        Setting active state

        :param active_state:
        :return:
        """
        self._active_state = active_state

    @property
    def forces(self):
        """
        :return: Forces list
        """
        return self._forces

    @forces.setter
    def forces(self, forces):
        """
        Setting forces

        :param forces:
        :return:
        """
        self._forces = forces

    def add_force(self, force):
        """
        Add new force to forces list.

        :param force:
        :return:
        """
        self._forces.append(force)

    @property
    def constraints(self):
        """
        :return: Constraints list
        """
        return self._constraints

    @constraints.setter
    def constraints(self, constraints):
        """
        Setting constraints

        :param constraints:
        :return:
        """
        self._constraints = constraints

    def add_constraint(self, constraint):
        """
        Add new constraint to constraints list

        :param constraint:
        :return:
        """
        self._constraints.append(constraint)

    def to_dict(self):
        """
        Converting HW component to dictionary

        :return: Dictionary
        """
        desc = HWComponent.to_dict(self)
        desc[self._name].update({ComponentDesc.CLOCK: self._clock.name})
        states_desc_list = [state.to_dict() for state in self._power_states]
        forces_desc_list = [force.to_dict() for force in self._forces]
        constraints_desc_list = [constraint.to_dict() for constraint in self._constraints]
        desc[self._name][StateDesc.POWER_STATES] = states_desc_list
        desc[self._name][StateDesc.ACTIVE_STATE] = self.active_state.to_dict()
        desc[self._name][StateDesc.FORCES] = forces_desc_list
        desc[self._name][StateDesc.CONSTRAINTS] = constraints_desc_list
        return desc

    @staticmethod
    def load_power_states(states_desc_list):
        """
        Loads power states from list of dictionaries

        :param states_desc_list: list of dictionaries that represents power states
        :return: list of States
        """
        if states_desc_list is None:
            return None
        states = [PowerState.load(state_desc) for state_desc in states_desc_list]
        return states


class ConnectableHWComponent(HWComponent):
    """
    Hardware component that can be connected - it may have initiators or target or both.
    """
    def __init__(self, initiators=None, targets=None, **kwargs):
        super(ConnectableHWComponent, self).__init__(**kwargs)
        self._initiators = initiators if initiators is not None else list()
        self._targets = targets if targets is not None else list()

    def add_initiator(self, initiator):
        """
        Adding new initiator to initiators list if new initiator does not exist.

        :param initiator:
        :return:
        """
        if initiator not in self._initiators:
            self._initiators.append(initiator)

    def del_initiator(self, initiator_name):
        """
        Deleting initiator by name if initiator exist, nothing happens if it does not exist.

        :param initiator_name:
        :return:
        """
        to_del = None
        for i in self._initiators:
            if i == initiator_name:
                to_del = i
                break
        if not to_del:
            self._initiators.remove(to_del)

    def add_target(self, target):
        """
        Adding new target to targets list if new target does not exist.

        :param target:
        :return:
        """
        if target not in self._targets:
            self._targets.append(target)

    def del_target(self, target_name):
        """
        Deleting target by name if target exist, nothing happens if it does not exist.

        :param target_name:
        :return:
        """
        to_del = None
        for t in self._targets:
            if t == target_name:
                to_del = t
                break
        if not to_del:
            self._targets.remove(to_del)

    @property
    def initiators(self):
        """
        :return: Initiators list
        """
        return self._initiators

    @property
    def targets(self):
        """
        :return: Targets list
        """
        return self._targets

    def to_dict(self):
        """
        Converting connectable hw component to dictionary.

        :return: Dictionary
        """
        desc = HWComponent.to_dict(self)
        desc[self.name] = defaultdict(list)
        for initiator in self._initiators:
            desc[self.name][ComponentDesc.INITIATORS].append({ComponentDesc.TYPE: initiator.type,
                                                              ComponentDesc.NAME: initiator.name})
        for target in self._targets:
            desc[self.name][ComponentDesc.TARGETS].append({ComponentDesc.TYPE: target.type,
                                                           ComponentDesc.NAME: target.name})
        return desc


class GeneralHWComponent(TickingHWComponent, ConnectableHWComponent):
    """
    General Hardware component with clock and connections.

    :param name: Name
    :param clock: clock
    :param _type: component type - one of ResourceDesc
    :param initiators: initiators list
    :param targets: targets list
    :param power_states: sleep power states list
    :param active_state: active power state
    :param forces: forces list
    :param constraints: constraints list
    """
    def __init__(self, name, clock: Clock, _type, initiators=None, targets=None, power_states=None, active_state=None,
                 forces=None, constraints=None):
        super(GeneralHWComponent, self).__init__(name=name, clock=clock, _type=_type, initiators=initiators,
                                                 targets=targets, power_states=power_states, active_state=active_state,
                                                 forces=forces, constraints=constraints)

    def to_dict(self):
        """
        Converting general hw component to dictionary.

        :return: Dictionary
        """
        ticking_desc = TickingHWComponent.to_dict(self)
        connectable_desc = ConnectableHWComponent.to_dict(self)
        ticking_desc[self._name].update(connectable_desc[self._name])
        return ticking_desc


# Global singleton clock
class GlobalClock:
    """
    Global system clock. default period is 0.01us.
    """
    class __GlobalClock(Clock):
        def __init__(self, name, period):
            super().__init__(name, period)

    instance = None

    def __init__(self, name, period):
        if not GlobalClock.instance:
            GlobalClock.instance = GlobalClock.__GlobalClock(name, period)
        else:
            GlobalClock.instance.period = period

    @staticmethod
    def set_period(period):
        if not GlobalClock.instance:
            GlobalClock.instance.period = period


GlobalClock(GLOBAL_CLOCK_NAME, GLOBAL_CLOCK_PERIOD_US)
