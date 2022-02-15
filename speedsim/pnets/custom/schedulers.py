from pnets.simulation import EVENTS, ResourceState, Scheduler


class BFScheduler(Scheduler):
    """
    Custom BigFirst scheduler, inherits from template simple scheduler, prefers to run on Big Core.
    it implements resource specific runtime adjustment.
    HW: # Big cores and # Atoms.
    Scheduling:
        - if transition is mapped to big core and no big core found then map it to Atom.
        in this case, adjust transition runtime. multiply it by Factor
        adding adjustment attribute is done in scheduler definition
    """
    BIG_CORE = "CPU"
    ATOM = "ATOM"

    def __init__(self, sim, atom_scale_factor=1):
        Scheduler.__init__(self, sim)
        for resource in self._sim.get_resources():
            if resource.resource_type == self.ATOM:
                resource.attach_attribute("scale_factor", atom_scale_factor)

    def schedule_transition(self, transition):
        """
        Find resource to execute specified transition state on.
        if transition is mapped to Big Core and Big Core is busy, map it to Atom and adjust runtime
        :param transition: TransitionState
        # """
        resource = super().schedule_transition(transition)
        if resource is not None:
            if resource.resource_type == self.ATOM:
                transition.runtime = transition.runtime * resource.get_attribute("scale_factor")
            return resource

        if self.BIG_CORE in transition.resource_types:
            for resource in self._sim.get_resources():
                if resource.resource_type == self.ATOM and resource.executing is None:
                    transition.runtime = transition.runtime * resource.get_attribute("scale_factor")
                    return resource
        return None


class NaiveRRScheduler:
    """
    Custom Naive round robin scheduler, it implements resource specific runtime adjustment.
    It manages the resources by itself
    HW: # Big cores and # Atoms.
    Scheduling:
        - Round robin between Big Core and Atom, run time of tasks that are executed on Atom is adjusted and
          multiplied by factor
        adding adjustment attribute is done in scheduler definition
    """
    BIG_CORE = "CPU"
    ATOM = "ATOM"

    def __init__(self, sim, count=2, atom_scale_factor=1):
        self._sim = sim
        self._free_resources = []
        self._busy_resources = []

        for i in range(0, count):
            self._free_resources.append(ResourceState(resource_type=self.BIG_CORE, index=i))
            atom = ResourceState(resource_type=self.ATOM, index=i)
            atom.attach_attribute("scale_factor", atom_scale_factor)
            self._free_resources.append(atom)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_resource_release)

    def schedule_transition(self, transition):
        """
        Queue of resources ordered in round robin, resource got freed is inserted to end of queue.
        Big Core, Atom, Big Core, Atom,....
        :param transition: TransitionState
        # """
        if transition is None:
            raise ValueError("Can't schedule None transition")

        if transition.resource_types is None:
            return ResourceState("NULL", 0)

        if len(self._free_resources) == 0:
            return None

        resource = self._free_resources.pop(0)
        if resource.resource_type == self.ATOM and resource.executing is None:
            transition.runtime = transition.runtime * resource.get_attribute("scale_factor")
        self._busy_resources.append(resource)
        return resource

    def on_resource_release(self, event):
        i = 0
        while i < len(self._busy_resources):
            resource = self._busy_resources[i]
            if resource.executing is None:
                resource = self._busy_resources.pop(i)
                self._free_resources.append(resource)
            else:
                i += 1


class OracleScheduler(Scheduler):
    """
    Custom scheduler, inherits from template simple scheduler, it implements resource specific runtime adjustment.
    HW: # Big cores and # Atoms.
    Scheduling:
        All tasks with run time lower than 50 goes to Atom
    """
    BIG_CORE = "CPU"
    ATOM = "ATOM"

    def __init__(self, sim, atom_scale_factor=1):
        Scheduler.__init__(self, sim)
        for resource in self._sim.get_resources():
            if resource.resource_type == self.ATOM:
                resource.attach_attribute("scale_factor", atom_scale_factor)

    def schedule_transition(self, transition):
        """
        Find resource to execute specified transition state on according to scheduling algo.
        # """

        big_cores = [big_core for big_core in self._sim.get_resources() if big_core.resource_type == self.BIG_CORE]
        small_cores = [small_core for small_core in self._sim.get_resources() if small_core.resource_type == self.ATOM]
        if transition.runtime > 50:
            for big_core in big_cores:
                if big_core.executing is None:
                    return big_core
        else:
            for small_core in small_cores:
                if small_core.executing is None:
                    transition.runtime = transition.runtime * small_core.get_attribute("scale_factor")
                    return small_core

        resource = super().schedule_transition(transition)
        if resource is not None and resource.resource_type == self.ATOM:
            transition.runtime = transition.runtime * resource.get_attribute("scale_factor")
        return resource


class PowerScheduler:
    """
    Custom Power scheduler it implements resource power state machine for waking resources up.
    HW: # Big cores and # Atoms.
    Scheduling:
        - check resource state, if it's not C0 wake it up after 1us, if C0 then schedule transition
        adding resource state as dynamic attribute
    Scheduler take as input hw wake up latency dictionary: resource -> wake up latency
    """
    SLEEP = "C6"
    AWAKE = "C0"
    RESOURCE_STATE = "resource_state"
    WAKE_UP_LATENCY = "wake_up_latency"
    POWER_STATE_CHANGE_EVENT = "power_state_change_event"

    def __init__(self, sim, hw_wake_up_latency):
        self._sim = sim
        for resource in self._sim.get_resources():
            resource.attach_attribute(self.RESOURCE_STATE, self.SLEEP)
            wake_up_latency = hw_wake_up_latency.get(resource.resource_type, 0)
            resource.attach_attribute(self.WAKE_UP_LATENCY, wake_up_latency)

    def schedule_transition(self, transition):
        """
        Find resource to execute specified transition state on.
        Check transition resource state - if state is not C0 then wait wake_up_latency...
        :param transition: TransitionState
        """
        if transition is None:
            raise ValueError("Can't schedule None transition")

        if transition.resource_types is None:
            return ResourceState("NULL", 0)

        for resource in self._sim.get_resources():
            if resource.resource_type in transition.resource_types and resource.executing is None:
                if resource.get_attribute(self.RESOURCE_STATE) == self.SLEEP:
                    self._sim.insert_event(self.POWER_STATE_CHANGE_EVENT,
                                           self._sim.now + resource.get_attribute(self.WAKE_UP_LATENCY),
                                           lambda: self.wake_up_resource(resource))
                    return None
                else:
                    return resource
        return None

    def wake_up_resource(self, resource):
        resource.attach_attribute(self.RESOURCE_STATE, self.AWAKE)
