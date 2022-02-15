"""
State manager is managing HW components states according relevant algorithm.
Each hw component may be:
    * active: C0
    * sleep: C6
Eah hw component defines its states by entry latency (time to be idle so it can go to sleep)
and exit latency (time take to go from C0 to C6
"""
from collections import namedtuple
from enum import Enum

from pandas import DataFrame

from asap.hw import ComponentState
from asap.strings import NAME_SEPARATOR


class CStates(Enum):
    C0 = "C0"
    C6 = "C6"


class CState:
    """
    Definition of a state
    """
    def __init__(self, state, entry_latency: float = 0.0, exit_latency: float = 0.0):
        """
        :param state: from CStates enum
        :param entry_latency: in us
        :param exit_latency: in us
        """
        self._state = state
        self._entry_latency = entry_latency
        self._exit_latency = exit_latency

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def entry_latency(self):
        return self._entry_latency

    @entry_latency.setter
    def entry_latency(self, value):
        self._entry_latency = value

    @property
    def exit_latency(self):
        return self._exit_latency

    @exit_latency.setter
    def exit_latency(self, value):
        self._exit_latency = value


state_event = namedtuple('StateEvent', ('TIME', 'RESOURCE', 'C_STATE'))


class StatesManager:
    """
    Managing HW components and system states.
    For each HW resource saves state with entry latency and exit latency.
    Updates ip states each period of time
    C_STATES: list of states in ip
    C_STATE: current resource state
    WAKE_UP_EVENT: event to push to simulation once resource should be awake
    WAITING: resource is waiting to be waked up, no need to request wake up again
    IDLE_TIME: amount of time resource was idle till now
    """
    C_STATES = "C_STATES"
    C_STATE = "C_State"
    WAKE_UP_EVENT = "WAKE_UP_EVENT"
    WAITING = "WAITING"
    IDLE_TIME = "IDLE_TIME"

    def __init__(self, sim, apm, system_platform, system_states):
        """
        :param sim: simulator to push wake up events to.
        :param apm: abstract power management
        :param system_platform:
        :param system_states: list of system states
        """
        self._sim = sim
        self._apm = apm
        self._sys_platform = system_platform
        self._system_states = system_states
        self._states_data = list()

    def is_resource_awake(self, resource):
        """
        Checks if resource is in C0 or C6
        :param resource:
        :return: True/False
        """
        if resource.get_attribute(self.C_STATE).state == CStates.C0:

            return True
        return False

    def pending_task_on_resource(self, resource):
        """
        Task waits resource to wake up
        :param resource:
        :return:
        """
        c6_state = self._get_resource_state(resource, CStates.C6)
        if c6_state is None:
            wake_up_latency = 0
        else:
            wake_up_latency = c6_state.exit_latency
        self._sim.insert_event(self.WAKE_UP_EVENT,
                               self._sim.now + wake_up_latency,
                               lambda: self._wake_up_resource(resource))
        resource.attach_attribute(self.WAITING, True)

    def _get_resource_state(self, resource, _state):
        """
        :param resource:
        :param _state: state enum (C0, C6,...)
        :return: CState
        """
        states = resource.get_attribute(self.C_STATES)
        if not states:
            return None
        for state in states:
            if state.state == _state:
                return state
        return None

    def _wake_up_resource(self, resource):
        """
        Wake up the resource, move its state to C0 and update the apm
        :param resource:
        :return:
        """
        resource.attach_attribute(self.C_STATE, self._get_resource_state(resource, CStates.C0))
        r = resource.ip.name + NAME_SEPARATOR + resource.name
        self._states_data.append(state_event(TIME=self._sim.now, RESOURCE=r, C_STATE=CStates.C0.value))
        resource.attach_attribute(self.WAITING, False)
        self._apm.resource_ready(resource)

    def update_resources(self, next_trigger):
        """
        Check idle resources and request to go to sleep.
        :param next_trigger:
        :return:
        """
        for resource in self._sys_platform.get_all_drivers() + self._sys_platform.get_all_executing_units():
            if resource.state == ComponentState.FREE:
                c6_state = self._get_resource_state(resource, CStates.C6)
                if not resource.get_attribute(self.WAITING) and \
                        resource.get_attribute(self.C_STATE).state != c6_state.state:
                    last_idle = resource.get_attribute(self.IDLE_TIME)
                    new_idle = last_idle + next_trigger
                    resource.attach_attribute(self.IDLE_TIME, new_idle)
                    # if idle for too long
                    if new_idle > c6_state.entry_latency:
                        # print("Going to sleep ", resource.ip.name, resource.name)
                        resource.attach_attribute(self.C_STATE, c6_state)
                        r = resource.ip.name + NAME_SEPARATOR + resource.name
                        self._states_data.append(state_event(TIME=self._sim.now, RESOURCE=r, C_STATE=CStates.C6.value))
            else:
                resource.attach_attribute(self.IDLE_TIME, 0)

    def executing_resource(self, resource):
        resource.attach_attribute(self.WAITING, False)

    def get_cstates_data(self):
        return DataFrame(self._states_data)


class CStatesBuilder:
    """
    Builds C states in all system platform resources according to required input.
    Any new builders should inherit and implement instantiate states
    """
    def __init__(self, sys_platform):
        self._sys_platform = sys_platform

    def instantiate_states(self, *args):
        """
        Instantiating default
        :param args:
        :return:
        """
        for res in self._sys_platform.get_all_executing_units() + self._sys_platform.get_all_drivers():
            c0_state = CState(CStates.C0)
            if res.ip.name == "GT":
                c6_state = CState(CStates.C6, entry_latency=12, exit_latency=15)
            else:
                c6_state = CState(CStates.C6, entry_latency=10, exit_latency=10)
            res.attach_attribute(StatesManager.C_STATE, c0_state)
            res.attach_attribute(StatesManager.IDLE_TIME, 0)
            res.attach_attribute(StatesManager.WAITING, False)
            res.attach_attribute(StatesManager.C_STATES, [c0_state, c6_state])
