"""
Petri-Net simulation
"""
import functools
import math
import sys
import weakref
from collections import namedtuple
from enum import Enum
from heapq import heapify, heappop, heappush

import pandas

import pnets.attributes as PnAttr
from pnets.pn_model import PnmlModel


class SimulationError(Exception):
    """
    Raised by simulator. Provides additional properties.
    """
    def __init__(self, time=0.0, message=None):
        super().__init__(message)
        self.time = time


class BufferOverrunError(SimulationError):
    """
    Raised when a buffer is full when a token needs to be delivered.
    """
    def __init__(self, time=0.0, message=None, place_id=None):
        super().__init__(time=time, message=message)
        self.place_id = place_id


class State:
    """
    Parent of all required states, dynamic model attributes.
    """
    def attach_attribute(self, attribute, value):
        self.__dict__[attribute] = value

    def get_attribute(self, attribute, default=None):
        return self.__dict__.get(attribute, default)

    def get_pnml_attribute(self, attribute):
        return None


class _PlaceState(State):
    """
    Hold current place state (number of tokens)
    """
    def __init__(self, place, size, count=0):
        super().__init__()
        self.place = place  # PnmlModel.Place() reference
        self.count = count  # current number of tokens
        self.size = size    # max number of tokens
        self.reserved = 0   # number of tokens reserved by a running preceeding transition
        self.output_transitions = []  # references to TransitionState
        self.input_transitions = []  # references to TransitionState

    def get_pnml_attribute(self, attribute):
        return self.place.get_attribute(attribute)


class TransitionState(State):
    """
    Holds current transition state
    """
    WAITING = 0    # waiting for tokens
    EXECUTING = 1  # executing
    READY = 2      # waiting for resource

    PlaceInfo = namedtuple('PlaceInfo', ('place', 'count'))

    def __init__(self, transition, resource_types, runtime, switch_overhead):
        super().__init__()
        self.transition = transition    # PnmlModel.Transition reference
        self.start_time = 0             # last start time
        self.resource_types = resource_types  # resource types list
        self.runtime = runtime          # Holds task run time - might be changed according to extensions
        self.orig_runtime = runtime     # Holds original run time given to task when created
        self.switch_overhead = switch_overhead
        self.state = TransitionState.WAITING
        self.input_places = []
        self.output_places = []
        self.end_event = None           # End event of transition - added once it get executed
        self.resource = None            # Resource transition is executed on
        self.priority = transition.get_attribute(PnAttr.PRIORITY, 0)

    def get_pnml_attribute(self, attribute):
        return self.transition.get_attribute(attribute)


class ResourceState(State):
    """
    Holds current resource state
    """
    __slots__ = ('resource_type', 'index', 'executing')

    def __init__(self, resource_type, index):
        super().__init__()
        self.resource_type = resource_type
        self.index = index
        self.executing = None  # currently executing transition


SIM_EVENT_START = 'START'
SIM_EVENT_FINISH = 'FINISH'
SIM_EVENT_TRANSITION = 'TRANSITION'
SIM_EVENT_RESOURCE = 'RESOURCE'
SIM_EVENT_RESOURCE_IDX = 'RESOURCE_IDX'
SIM_EVENT_FEATURE = 'FEATURE'
SIM_EVENT_DURATION = 'DURATION'
SIM_UTILIZATION = 'UTILIZATION'
NAN = float('NaN')

# Each simulation returns a table of simulation events
SimEvent = namedtuple('SimEvent', (SIM_EVENT_START, SIM_EVENT_FINISH, SIM_EVENT_TRANSITION, SIM_EVENT_RESOURCE,
                                   SIM_EVENT_RESOURCE_IDX, SIM_EVENT_DURATION))


class ClockEvent:
    """
    Simulator clock events.
    The simulator processes clock events according to chronological order of the "clock".
    """
    __slots__ = ('name', 'clock', 'execute')

    def __init__(self, name, clock=NAN, execute=None):
        self.name = name
        self.clock = clock
        self.execute = execute


# item used for heap sorted queue
_HeapItem = namedtuple('_Event', ('clock', 'index', 'clock_event'))


class EVENTS(Enum):
    """
    TASK_READY: Task can start, ready to be executed.
        - Emitting params: transition
    TASK_END: Task finished executing.
        - Emitting params: transition, resource
    TASK_EXECUTE: Task executed - found free resource and started to run.
                                  Emitted just before scheduling the task end event.
        - Emitting params: transition, resource
    DELIVER_TOKENS: Deliver token to next place.
        - Emitting params: place
    START_SCHEDULE: Schedule next token for a periodic start node.
        - Emitting params: place
    CLOCK_TICK: Emitted when current clock time is about to change after processing all events
                for the current clock tick.
        - Params: None
    TASK_UPDATE: Executed tasks need to be updated because of a change in the system.
        - Emitting params: transition
    """
    TASK_READY = "TASK_READY"
    TASK_END = "TASK_END"
    TASK_EXECUTE = "TASK_EXECUTE"
    DELIVER_TOKENS = "DELIVER_TOKENS"
    START_SCHEDULE = "NEXT_START_TASK_SCHEDULE"
    CLOCK_TICK = "CLOCK_TICK"
    TASK_UPDATE = "TASK_UPDATE"


class Scheduler:
    """
    Template simple scheduler, schedule tasks on proper free resource
    """
    def __init__(self, sim):
        self._sim = sim

    def schedule_transition(self, transition):
        """
        Find resource to execute specified transition state on.
        :param transition: TransitionState
        :return: free resource from possible transition resources or None if no available resource found.
        """
        if transition is None:
            raise ValueError("Can't schedule None transition")

        if transition.resource_types is None:
            return ResourceState("NULL", 0)
        for resource in self._sim.get_resources():
            if resource.resource_type in transition.resource_types and resource.executing is None:
                return resource
        return None


class Event(list):
    """
    Signal interface similar to Qt
    """
    def connect(self, func):
        if hasattr(func, '__self__'):
            self.append(weakref.WeakMethod(func))
        else:
            self.append(weakref.ref(func))

    def disconnect(self, func):
        for i in range(len(self)-1, -1, -1):
            if func == self[i]():
                self.pop(i)

    def emit(self, *args, **kwargs):
        delme = []
        for i, ref in enumerate(self):
            if ref() is None:
                delme.append(i)
            else:
                ref()(*args, **kwargs)

        if len(delme):
            for i in reversed(delme):
                self.pop(i)


class Simulator:
    """
    Simple Petri-net simulator.

    :param pn_model: PetriNet model for simulation
    :param resources: map ResourceType -> count

    Assumptions:
        * delay/runtime units are microseconds
        * freq units are Hz
    """
    def __init__(self, pn_model, resources):
        self._model = pn_model
        self._event_index = 0
        self._event_queue = []  # sorted list of future simulator events
        self._clock = 0         # current simulation time
        self._ready_queue = []  # list of transitions potentially ready for execution
        self._sim_events = []   # simulation results
        self._scheduler = None
        self._events = {}  # Dictionary of Event name -> Event object

        # states:
        self._places = {}
        self._transitions = {}

        # initialize resources
        self._resources = []
        for resource_type, resource_count in resources.items():
            for i in range(resource_count):
                self._resources.append(ResourceState(resource_type=resource_type, index=i))

        # initialize place states, transition states and connections:
        for net in self._model.nets:
            for place in net.places:
                if place.type == PnmlModel.Place.Type.START:
                    count = 0
                    s = place.get_attribute(PnAttr.ITERATIONS)
                    size = int(s+1) if s is not None else 1
                elif place.type == PnmlModel.Place.Type.END:
                    count = 0
                    size = math.inf
                else:
                    count = place.get_attribute(PnAttr.INIT_COUNT) or 0
                    size = place.get_attribute(PnAttr.BUFFER_SIZE)
                self._places[place.id] = _PlaceState(place=place, size=size, count=count)

            for trans in net.transitions:
                resource = trans.get_attribute(PnAttr.HW_RESOURCE)
                if resource is not None:
                    resource = resource.split(',')
                    for r in resource:
                        if r not in resources:
                            raise(Exception("Transition " + str(trans.id) +
                                            " is assigned to resource " + r + " but no such resource was specified"))
                self._transitions[trans.id] = TransitionState(transition=trans,
                                                              resource_types=resource,
                                                              runtime=trans.get_attribute(PnAttr.RUNTIME),
                                                              switch_overhead=max(0, trans.get_attribute(
                                                                  PnAttr.SWITCH_OVERHEAD) or 0.0))
            for arc in net.arcs:
                src, target = arc.src, arc.target
                if src in self._places:
                    if target not in self._transitions:
                        raise(Exception("Unexpected transition id {1} for arc {0} -> {1}".format(src, target)))
                    self._places[src].output_transitions.append(self._transitions[target])
                    self._transitions[target].input_places.append(TransitionState.PlaceInfo(
                        self._places[src], arc.get_attribute(PnAttr.WEIGHT)))
                else:
                    if target not in self._places:
                        raise(Exception("Unexpected place id {1} for arc {0} -> {1}".format(src, target)))
                    self._transitions[src].output_places.append(TransitionState.PlaceInfo(
                        self._places[target], arc.get_attribute(PnAttr.WEIGHT)))
                    self._places[target].input_transitions.append(self._transitions[src])

    def connect_to_event(self, event_name, func):
        event = self._events.get(event_name, None)
        if event is None:
            event = Event()
            self._events[event_name] = event
        event.connect(func)

    def emit(self, event_name, *args, **kwargs):
        """
        Emit specified event with arguments

        :param event_name: one of Event.* values
        :param args: optional arguments
        :param kwargs: optional keyed arguments
        :return: True if events emitted, False otherwise
        """
        event = self._events.get(event_name, None)
        if event is None:
            return False
        event.emit(*args, **kwargs)
        return True

    def run(self, duration):
        """
        Run simulation for the specified duration

        :param duration: duration of time to run (usec)
        """
        max_clock = self._clock + duration

        # schedule initial tokens for start events:
        for place in self._places.values():
            if place.place.type == PnmlModel.Place.Type.START:
                self._schedule_start_events(place, self._clock, max_clock)

        while self._clock < max_clock:
            # go to next clock:
            if len(self._event_queue) == 0:
                if not self.emit(EVENTS.CLOCK_TICK) or len(self._event_queue) == 0:
                    break

            next_clock = self._event_queue[0].clock
            if next_clock > max_clock:
                break

            if next_clock != self._clock:
                if self.emit(EVENTS.CLOCK_TICK):
                    # must refresh next clock after emitting events:
                    if len(self._event_queue) == 0:
                        break
                    next_clock = self._event_queue[0].clock
                    if next_clock > max_clock:
                        break

            # pump out all events with the same clock value:
            self._clock = next_clock
            while len(self._event_queue) and self._event_queue[0].clock == self._clock:
                # event = self._event_queue.pop(0)
                event = heappop(self._event_queue)
                event.clock_event.execute()

            # find a transition to schedule from list of previously observed ready transitions:
            i = 0
            while i < len(self._ready_queue):
                tran = self._ready_queue[i]
                resource = self.scheduler.schedule_transition(tran)
                if resource is not None and self._is_ready(tran):
                    # need to check if transition is still ready if there are competing transitions
                    self._ready_queue.pop(i)
                    self._execute(tran, resource)
                    # i = 0 ??
                else:
                    i += 1

        # NOTE: some tasks may be still executing by the time we finish running this function
        self._report_uncompleted()
        return pandas.DataFrame(self._sim_events)

    def get_executing_tasks(self):
        """
        Returns a list of (TransactionState, ResourceState) for all currently executing transaction
        """
        return [(res.executing, res) for res in self._resources if res.executing is not None]

    def get_events(self):
        return self._event_queue

    def get_ready_tasks(self):
        return self._ready_queue

    @property
    def now(self):
        return self._clock

    def step(self, step):
        """
        Make sim take step forward in clock by adding step value

        :param step: step duration in us
        :return:
        """
        self._clock += step

    def _report_uncompleted(self):
        # all executing event are in queue
        for tran_state, resource in self.get_executing_tasks():
            self._sim_events.append(SimEvent(
                START=tran_state.start_time,
                FINISH=NAN,
                TRANSITION=tran_state.transition.id,
                RESOURCE=resource.resource_type,
                RESOURCE_IDX=resource.index,
                DURATION=NAN
            ))

    def _is_ready(self, trans_state):
        """
        Check if transition has enough input tokens in all input places.

        :param trans_state: _TransitionState
        """
        consumed = {}  # record consumed tokens per place to properly support loop arcs
        for place, count in trans_state.input_places:
            if count > place.count:
                return False
            consumed[id(place)] = count

        for place, count in trans_state.output_places:
            if count + place.reserved + place.count - consumed.get(id(place), 0) > place.size:
                return False
        return True

    def _schedule_start_events(self, place, clock, max_clock):
        """
        Schedule start events in [clock..max_clock) range

        :param place: place state
        :param clock: left clock bound
        :param max_clock: right clock bound
        """
        if len(place.output_transitions) != 1:
            raise(Exception("Incorrect connectivity for start place {0} ({1}, expected 1)".format(
                place.place.id, len(place.output_transitions))))
        delay = place.place.get_attribute(PnAttr.START_DELAY) or 0
        freq = place.place.get_attribute(PnAttr.FREQUENCY) or 0
        iterations = place.place.get_attribute(PnAttr.ITERATIONS) or 1
        invokes = place.get_attribute(PnAttr.INVOKES) or 0
        if (freq > 0 or invokes < iterations) and delay < max_clock:
            if freq > 0:
                period = 1 / freq * 1e6  # NOTE: assuming usec units for delay
            else:
                period = place.place.get_attribute(PnAttr.WAIT_DELAY) or 1
            first = max(math.ceil((clock - delay) / period), 0)
            self.insert_event(EVENTS.START_SCHEDULE, delay + first * period,
                              lambda: self._schedule_next_start(place, max_clock))
            self.insert_event(EVENTS.DELIVER_TOKENS, delay + first * period, lambda: self._deliver_tokens(place, 1))
            place.attach_attribute(PnAttr.INVOKES, invokes+1)
        else:
            if clock <= delay < max_clock:
                self.insert_event(EVENTS.DELIVER_TOKENS, delay, lambda: self._deliver_tokens(place, 1))

    def _schedule_next_start(self, place, max_clock):
        """
        Schedule next token for a periodic start node.

        :param place: place state
        :param max_clock: current max simulation clock
        """
        self.emit(EVENTS.START_SCHEDULE, place)
        freq = place.place.get_attribute(PnAttr.FREQUENCY)
        if freq is not None and freq > 0:
            period = 1 / freq * 1e6  # NOTE: assuming usec units for delay
            iterations = sys.maxsize
        else:
            period = place.place.get_attribute(PnAttr.WAIT_DELAY) or 0
            iterations = place.place.get_attribute(PnAttr.ITERATIONS) or 1
        invokes = place.get_attribute(PnAttr.INVOKES, 1)
        if self._clock + period < max_clock and invokes < iterations:
            self.insert_event(EVENTS.DELIVER_TOKENS, self._clock + period, lambda: self._deliver_tokens(place, 1))
            self.insert_event(EVENTS.START_SCHEDULE, self._clock + period,
                              lambda: self._schedule_next_start(place, max_clock))
            place.attach_attribute(PnAttr.INVOKES, invokes + 1)

    def _execute(self, trans_state, resource):
        """
        Start executing the specified transition on the specified resource.

        :param trans_state:
        """
        assert(trans_state != TransitionState.EXECUTING)

        # consume input tokens
        for place, count in trans_state.input_places:
            assert(place.count >= count)
            place.count -= count

        # reserve space for output tokens
        for place, count in trans_state.output_places:
            assert(place.reserved + place.count <= place.size)
            place.reserved += count

        trans_state.state = TransitionState.EXECUTING
        resource.executing = trans_state
        trans_state.resource = resource
        trans_state.start_time = self._clock + trans_state.switch_overhead

        self.emit(EVENTS.TASK_EXECUTE, trans_state, resource)

        trans_state.end_event = self.insert_event(EVENTS.TASK_END,
                                                  self._clock + trans_state.switch_overhead + trans_state.runtime,
                                                  lambda: self._done_executing(trans_state, resource))

        # Check the predecessors transitions of started one if they can start executing again:
        # Since it consumed tokens in place
        for place, count in trans_state.input_places:
            for tran in place.input_transitions:
                if self._is_ready(tran):
                    self.insert_event(EVENTS.TASK_READY, self._clock, functools.partial(self._mark_ready, tran))

    def _queue_event(self, clock_event):
        """
        Queueing ClockEvent into the queue of events sorted by clock.
        """
        # i = 0
        # while i < len(self._event_queue):
        #     if clock_event.clock < self._event_queue[i].clock:
        #         break
        #     i += 1
        # self._event_queue.insert(i, clock_event)
        heappush(self._event_queue, _HeapItem(clock_event.clock, self._event_index, clock_event))
        self._event_index += 1

    def insert_event(self, event_name, clock, func):
        """
        Insert a ClockEvent into the queue of events sorted by clock.
        """
        event = ClockEvent(event_name, clock, func)
        self._queue_event(event)
        return event

    def cancel_event(self, clock_event: ClockEvent):
        """
        Remove a ClockEvent from the queue of events.
        """
        # if clock_event in self._event_queue:
        #    self._event_queue.remove(clock_event)
        for idx, ev in enumerate(self._event_queue):
            if ev.clock_event == clock_event:
                self._event_queue.pop(idx)
                heapify(self._event_queue)
                break

    def update_event(self, clock_event: ClockEvent):
        """
        Update a ClockEvent from the queue of events to new clock position.
            - remove from current place
            - insert back to appropriate place
        """
        self.cancel_event(clock_event)
        self._queue_event(clock_event)

    def _done_executing(self, trans_state, resource):
        """
        Called when a transition finishes executing on the specified resource

        :param trans_state: TransitionState
        :param resource: ResourceState
        """
        self.emit(EVENTS.TASK_END, trans_state, resource)
        trans_state.state = TransitionState.WAITING
        trans_state.resource = None
        trans_state.end_event = None
        resource.executing = None
        self._sim_events.append(SimEvent(
            START=trans_state.start_time,
            FINISH=self._clock,
            TRANSITION=trans_state.transition.id,
            RESOURCE=resource.resource_type,
            RESOURCE_IDX=resource.index,
            DURATION=self._clock-trans_state.start_time
        ))

        # deliver output tokens:
        for place, count in trans_state.output_places:
            assert(place.reserved >= count)
            self._deliver_tokens(place, count)

        # check the transition that just finished in cases it can start executing again:
        if self._is_ready(trans_state):
            self.insert_event(EVENTS.TASK_READY, self._clock, lambda: self._mark_ready(trans_state))

    def _mark_ready(self, tran):
        """
        Mark transition as ready to execute and move it into the ready queue

        :param tran:
        """
        self.emit(EVENTS.TASK_READY, tran)
        if tran.state == TransitionState.WAITING:
            tran.state = TransitionState.READY
            if tran.priority > 0:
                i = 0
                while i < len(self._ready_queue):
                    queued_tran = self._ready_queue[i]
                    queues_tran_resources = set(queued_tran.resource_types)
                    tran_resources = set(tran.resource_types)
                    if len(queues_tran_resources.intersection(tran_resources)) > 0:
                        if tran.priority > queued_tran.priority:
                            self._ready_queue.insert(i, tran)
                            return
                    i += 1
            self._ready_queue.append(tran)

    def _deliver_tokens(self, place, count):
        """
        Deliver tokens to the specified place
        """
        self.emit(EVENTS.DELIVER_TOKENS, place)
        if place.reserved >= count:
            place.reserved -= count

        if place.count + count > place.size:
            raise BufferOverrunError(time=self._clock,
                                     message="Cannot deliver {} more tokens to {}".format(count, place.place.id),
                                     place_id=place.place.id)

        place.count += count

        # schedule new ready transitions:
        for other in place.output_transitions:
            if self._is_ready(other):
                self.insert_event(EVENTS.TASK_READY, self._clock, functools.partial(self._mark_ready, other))

    @property
    def scheduler(self):
        if self._scheduler is None:
            self._scheduler = Scheduler(self)
        return self._scheduler

    @scheduler.setter
    def scheduler(self, scheduler):
        self._scheduler = scheduler

    def add_resource(self, new_resource):
        index = 0
        for resource in self._resources:
            if resource.resource_type == new_resource:
                if resource.index > index:
                    index = resource.index
        self._resources.append(ResourceState(new_resource, index+1))

    def get_resources(self):
        return self._resources

    def set_resources(self, resources):
        self._resources = resources


def simulate_model(pn_model, resources, duration=1000000):
    """
    Simulate PN model and return pandas DataFrame with results

    :param pn_model:
    :param resources:
    :param duration:
    :return:
    """
    sim = Simulator(pn_model, resources)
    sim.scheduler = Scheduler(sim)
    return sim.run(duration)


def get_resource_utilization(results):
    """
    Compute utilization per resource type

    :param results: simulation results
    :return: dict (resource) -> pandas.Series()
    """
    result = {}

    for resource, rows in results.groupby(SIM_EVENT_RESOURCE):
        data = pandas.DataFrame([
            (v, 1) for v in rows[SIM_EVENT_START].values
        ] + [
            (v, -1) for v in rows[SIM_EVENT_FINISH].values if v is not NAN
        ], columns=['time', 'value'])
        data = data.groupby('time').sum().sort_index().reset_index()
        data = data[data['value'] != 0]
        data[SIM_UTILIZATION] = data['value'].cumsum()
        data[SIM_EVENT_DURATION] = data['time'].shift(-1) - data['time']
        data.drop('value', axis=1, inplace=True)
        data = data.iloc[:-1]
        data.set_index('time', inplace=True)

        result[resource] = data

    return result
