"""
States class definition file.
    - Base state with a name, leakage power and voltage.
    - Power state for sleep states with exit, enter and trigger latency.
    - Active state
"""
from typing import List

from .defaults import ActiveStates, GeneralPower, PowerStates
from .strings import NAME_SEPARATOR, ResourceDesc, StateDesc


class BaseState:
    """
    General power state of hardware component
    """
    def __init__(self, name=PowerStates.SLEEP_STATE,
                 reference_leakage_power=PowerStates.REFERENCE_LEAKAGE_POWER,
                 reference_voltage=PowerStates.REFERENCE_VOLTAGE):
        """
        :param name: State name
        :param reference_leakage_power:
        :param reference_voltage:
        """
        self._name = name
        self._reference_leakage_power = reference_leakage_power
        self._reference_voltage = reference_voltage

    @property
    def name(self):
        return self._name

    @property
    def reference_leakage_power(self):
        return self._reference_leakage_power

    @property
    def reference_voltage(self):
        return self._reference_voltage

    def to_dict(self):
        desc = dict()
        desc[self._name] = {StateDesc.LEAKAGE_POWER: self._reference_leakage_power,
                            StateDesc.VOLTAGE: self._reference_voltage}
        return desc


class PowerState(BaseState):
    """
    Sleep power state of hardware component
    """
    def __init__(self, name=PowerStates.SLEEP_STATE,
                 reference_leakage_power=PowerStates.REFERENCE_LEAKAGE_POWER,
                 reference_voltage=PowerStates.REFERENCE_VOLTAGE,
                 entrance_latency=PowerStates.ENTRANCE_LATENCY,
                 exit_latency=PowerStates.EXIT_LATENCY,
                 trigger=PowerStates.TRIGGER):
        """
        :param entrance_latency: time to enter the state in us
        :param exit_latency: time to exit from the state in us
        :param trigger: trigger time in us
        """
        super().__init__(name, reference_leakage_power, reference_voltage)
        self._entrance_latency = entrance_latency
        self._exit_latency = exit_latency
        self._trigger = trigger

    @property
    def entrance_latency(self):
        return self._entrance_latency

    @entrance_latency.setter
    def entrance_latency(self, entrance_latency):
        self._entrance_latency = entrance_latency

    @property
    def exit_latency(self):
        return self._exit_latency

    @exit_latency.setter
    def exit_latency(self, exit_latency):
        self._exit_latency = exit_latency

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger):
        self._trigger = trigger

    def to_dict(self):
        desc = super().to_dict()
        desc[self._name].update({StateDesc.ENTRANCE_LATENCY: self._entrance_latency,
                                 StateDesc.EXIT_LATENCY: self._exit_latency,
                                 StateDesc.TRIGGER_IN: self._trigger})
        return desc

    @staticmethod
    def load(desc):
        for name in desc.keys():
            desc = desc[name]
            return PowerState(name, desc[StateDesc.LEAKAGE_POWER], desc[StateDesc.VOLTAGE],
                              desc[StateDesc.ENTRANCE_LATENCY],
                              desc[StateDesc.EXIT_LATENCY], desc[StateDesc.TRIGGER_IN])


class ActiveState(BaseState):
    """
    Active power state of hardware component
    """
    def __init__(self, name=ActiveStates.ACTIVE_STATE,
                 reference_leakage_power=ActiveStates.REFERENCE_LEAKAGE_POWER,
                 reference_voltage=ActiveStates.REFERENCE_VOLTAGE,
                 reference_frequency=ActiveStates.REFERENCE_FREQUENCY,
                 reference_dynamic_power=ActiveStates.REFERENCE_DYNAMIC_POWER,
                 system_dependency=None):
        super().__init__(name, reference_leakage_power, reference_voltage)
        self._reference_frequency = reference_frequency
        self._reference_dynamic_power = reference_dynamic_power
        self._system_dependency = system_dependency if system_dependency is not None else 'NONE'

    @property
    def reference_frequency(self):
        return self._reference_frequency

    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = reference_frequency

    @property
    def reference_dynamic_power(self):
        return self._reference_dynamic_power

    @reference_dynamic_power.setter
    def reference_dynamic_power(self, reference_dynamic_power):
        self._reference_dynamic_power = reference_dynamic_power

    @property
    def system_dependency(self):
        return self._system_dependency

    @system_dependency.setter
    def system_dependency(self, value):
        if value is None:
            value = 'NONE'
        self._system_dependency = value

    def to_dict(self):
        desc = super().to_dict()
        desc[self._name].update({StateDesc.REFERENCE_FREQUENCY: self.reference_frequency,
                                 StateDesc.REFERENCE_DYNAMIC_POWER: self.reference_dynamic_power})
        return desc

    @staticmethod
    def load(desc):
        if desc is None:
            return None
        for name in desc.keys():
            desc = desc[name]
            return ActiveState(name, desc[StateDesc.LEAKAGE_POWER], desc[StateDesc.VOLTAGE],
                               desc[StateDesc.REFERENCE_FREQUENCY], desc[StateDesc.REFERENCE_DYNAMIC_POWER])


class StateTransition:
    """
    Transition states class defines transition between 2 states.
    State1 -> state2 after idle time
    """
    def __init__(self, from_state, to_state, idle_time):
        self._from_state = from_state
        self._to_state = to_state
        self._idle_time = idle_time

    @property
    def from_state(self):
        return self._from_state

    @from_state.setter
    def from_state(self, value):
        self._from_state = value

    @property
    def to_state(self):
        return self._to_state

    @to_state.setter
    def to_state(self, value):
        self._to_state = value

    @property
    def idle_time(self):
        return self._idle_time

    @idle_time.setter
    def idle_time(self, value):
        self._idle_time = value


class Condition:
    """
    A condition inside an expression.

    Condition consists of:
        - Hierarchical hw component name starting from parent ip. e.g. IA/VC0
        - Condition: =, <=
        - State: Power/Active state name

    example: (hw_component) ip/driver (condition) <= (power_state) C6

    :param hw_component: hw component name or the hw component itself,
                         the name needs to be full, example: "IP/Driver". Can use function in utils
                         get_full_hw_name(hw_component).
    :param condition: string, currently supports = or <=
    :param state_name:
    :param negate: if True, opposite of the condition will be taken

    """
    def __init__(self, hw_component, condition, state_name, negate=False):
        self._hw_component = hw_component
        if condition != StateDesc.EQUAL and condition != StateDesc.LESS_EQUAL:
            raise ValueError('The ' + str(condition) +
                             ' condition is not supported! Please use StateDesc.EQUAL or StateDesc.LESS_EQUAL')
        self._condition = condition
        self._state_name = state_name
        self._negate = negate

    @property
    def hw_component(self):
        if isinstance(self._hw_component, str):
            return self._hw_component
        else:
            return get_full_hw_name(self._hw_component)

    @property
    def condition(self):
        return self._condition

    @property
    def state_name(self):
        return self._state_name

    @property
    def negate(self):
        return self._negate

    def to_dict(self):
        """
        :return: { Hw Component: <full name>, Condition: <condition>, Power state: <state name> }
        """
        desc = dict()
        desc[ResourceDesc.HW_COMPONENT] = self.hw_component
        desc[StateDesc.CONDITION] = self.condition
        desc[StateDesc.POWER_STATE] = self.state_name
        desc[StateDesc.OPPOSITE] = self.negate
        return desc

    @staticmethod
    def load(desc):
        return Condition(desc[ResourceDesc.HW_COMPONENT], desc[StateDesc.CONDITION], desc[StateDesc.POWER_STATE],
                         desc[StateDesc.OPPOSITE])

    def __eq__(self, other):
        if not isinstance(other, Condition):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return \
            self.hw_component == other.hw_component and self.condition == other.condition and \
            self.state_name == other.state_name and self.negate == other.negate

    def __hash__(self):
        return hash((self.hw_component, self.condition, self.state_name, self.negate))


class Expression:
    """
    Boolean expression that contains multiple conditions of power states.
    All conditions must be answered so expressions will be too ("AND" between conditions).
    """
    def __init__(self, name=GeneralPower.EXPRESSION_NAME, conditions: List[Condition] = None):
        """
        :param name:
        :param conditions: list of conditions
        """
        self._name = name
        self._conditions = conditions if conditions is not None else list()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def conditions(self):
        return self._conditions

    def to_dict(self):
        """
        :return: { <name>: [ {condition dict}, ... ] }
        """
        desc = dict()
        desc[self._name] = list()
        for condition in self._conditions:
            desc[self._name].append(condition.to_dict())
        return desc

    @staticmethod
    def load(desc):
        conditions_list = list()
        name = None
        for name in desc.keys():
            for condition_desc in desc[name]:
                conditions_list.append(Condition.load(condition_desc))
        return Expression(name, conditions_list)

    def __eq__(self, other):
        if not isinstance(other, Expression):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.name == other.name and self.conditions == other.conditions

    def __hash__(self):
        return hash(tuple(self.conditions + [self.name]))

    def __add__(self, other):
        return Expression(self.name, self.conditions + other.conditions)


class HierarchyState:
    """
    System or IP state with idle time and expression for transition
    """
    def __init__(self, name, idle_time=GeneralPower.IDLE_TIME,
                 expression: Expression = None):
        self._name = name
        self._idle_time = idle_time
        self._expression = expression if expression is not None else Expression()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def idle_time(self):
        return self._idle_time

    @idle_time.setter
    def idle_time(self, idle_time):
        self._idle_time = idle_time

    @property
    def expression(self):
        return self._expression

    def to_dict(self):
        """
        :return: { <name>: { IDLE_TIME: <idle_time>, EXPRESSION: <expression_dict> }
        """
        desc = dict()
        desc[self._name] = {StateDesc.IDLE_TIME: self._idle_time, StateDesc.EXPRESSION: self._expression.to_dict()}
        return desc

    @staticmethod
    def load(desc):
        if desc is None:
            return None
        for name in desc.keys():
            return HierarchyState(name, desc[name][StateDesc.IDLE_TIME],
                                  Expression.load(desc[name][StateDesc.EXPRESSION]))


class Force(HierarchyState):
    """
    Force a module to enter a specific state

    :param state_name:
    :param idle_time:
    :param expression: Expression that activates the force
    """
    def __init__(self, state_name, idle_time=GeneralPower.IDLE_TIME,
                 expression: Expression = None):
        super().__init__(state_name, idle_time, expression)


class Constraint(HierarchyState):
    """
    Constrain a module to retain a certain state

    :param state_name:
    :param expression: Expression that activates the Constraint
    """
    def __init__(self, state_name, expression: Expression = None):
        super().__init__(state_name, 0, expression)


def get_full_hw_name(hw_component):
    """
    Returns the full hw name including father

    :param hw_component:
    :return: father_name/component_name
    """
    # TODO: OR - return full hierarchical name, recursive on father, could be nested hw
    if hw_component.type == ResourceDesc.EX_U or hw_component.type == ResourceDesc.DRIVER:
        if hw_component.ip is None:
            raise ValueError("Cant get full name of " + hw_component.name + " because its not in a platform.")
        return hw_component.ip.name + NAME_SEPARATOR + hw_component.name
    return hw_component.name
