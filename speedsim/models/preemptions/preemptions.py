from asap.schedulers import BaseSystemScheduler
from asap.strings import (ACTIVE_RUNTIME, RESOURCE, TASK, SchedulingState,
                          TaskMetaData)
from asap.workload import TYPES
from models.fabric.multi_memory import MultiMemoryExtension
from pnets.attributes import RUNNING_TRANSITIONS
from pnets.simulation import EVENTS, SimEvent, TransitionState
from speedsim import AnalysisExtension
from speedsim_utils import Logger


class RoundRobinScheduler(BaseSystemScheduler):
    """
    Tries to schedule regulary first, if all of the resources have executing tasks on them, then schedules the task
    to the resource with the least currently waiting tasks on it
    """
    def __init__(self, system_mgr):
        super().__init__(system_mgr)

    def schedule_task(self, task, mappings):
        if not mappings:
            # Empty mappings -> task is not mapped to any.
            self._update_unmapped_task(task)
            return None, SchedulingState.NULL

        no_preemption_resource, state = super().schedule_task(task, mappings)
        if no_preemption_resource is not None and state != SchedulingState.NAN:
            return no_preemption_resource, SchedulingState.SCHEDULED

        # Did not find any free resource
        min_running_tasks = None  # min value of running tasks on resource
        min_resource = None  # the resource with the least running tasks
        for mapping in mappings:
            resource = mapping.resource
            if task.type == TYPES.PROC or task.type == TYPES.GEN:
                resource_list = resource.executing_units
            else:
                resource_list = resource.drivers
            for r in resource_list:
                if r.get_attribute(RoundRobinExtension.TIME_SLICE) is not None:
                    resource_running_tasks_size = len(r.get_attribute(RoundRobinExtension.RUNNING_TRANSITIONS) or
                                                      list())
                    if min_resource is None or resource_running_tasks_size < min_running_tasks:
                        min_resource = r
                        min_running_tasks = resource_running_tasks_size

        resource = min_resource
        if resource is None:
            return None, SchedulingState.NAN

        resource.ip.set_resource_to_task(task, resource)
        self._update_system(task, resource)

        if task.type == TYPES.PROC or task.type == TYPES.GEN:
            self._update_proc_task(task, resource)
            return resource, SchedulingState.SCHEDULED

        self._update_mem_task(task, resource)
        return resource, SchedulingState.SCHEDULED

    def on_task_finish(self, task):
        resource = self._system_mgr.get_executing_task_resource(task)
        if resource is None:
            return
        resource.ip.remove_task(task)
        if len(resource.get_attribute(RUNNING_TRANSITIONS, list())) <= 1:
            super().on_task_finish(task)


class RoundRobinExtension:
    """
    Extension that lets resource run tasks with round robin algorythem
    """
    ROUND_ROBIN = 'ROUND_ROBIN'
    PRIORITY = 'PRIORITY'
    PREEMPTION_ALGOS = 'PREEMPTION_ALGOS'  # list of preemption algorythems on the resource
    RUNNING_TRANSITIONS = 'RUNNING_TRANSITIONS'  # list of running tasks on the resource with preemptions
    TIME_SLICE = 'TIME_SLICE'  # time slice for resource round robin algo in us
    TASK_START_TIME = 'TASK_START_TIME'

    # boolean attribute on the resource or task that represents if it's currently roundrobin
    ROUND_ROBIN_PROCESS = 'ROUND_ROBIN_PROCESS'
    ROUND_ROBIN_START_TIME = 'ROUND_ROBIN_START_TIME'
    END_EVENT_FIX_EVENT = 'END_EVENT_FIX_EVENT'
    RR_TIME_SLICE_FINISH_EVENT = 'RR_TIME_SLICE_FINISH_EVENT'  # Event name for finish round robin
    DONT_ADD = 'DONT_ADD'  # Dont add time attribute for waiting task

    def __init__(self, sim, system_mgr):
        self._sim = sim
        self._system_mgr = system_mgr
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self.on_task_execute)
        self._sim.connect_to_event(EVENTS.TASK_END, self.on_task_finish)
        self._sim.connect_to_event(EVENTS.TASK_UPDATE, self.check_time_slice)

    def _get_task(self, transition):
        """
        Getting task of speedSim transition
        :param transition:
        :return: Task
        """
        return transition.get_pnml_attribute(TASK)

    def _get_resource(self, resource):
        """
        Getting platform resource out of speedsim resource
        :param resource:
        :return:
        """
        if resource is None or resource.resource_type == 'NULL':
            return None
        return resource.get_attribute(RESOURCE)

    def on_task_execute(self, transition, resource):
        """
        If there are other tasks that run on the resource it sets the task in the wait list and activates the
        preemptions
        :param transition:
        :param resource:
        :return:
        """
        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if hw_resource.get_attribute(self.TIME_SLICE) is not None:
            task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, None)
            task.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
            task.attach_attribute(self.ROUND_ROBIN_START_TIME, None)
            task.attach_attribute(self.DONT_ADD, False)
            task.attach_attribute(ACTIVE_RUNTIME, 0)
            self.execute_round_robin(transition, resource)

        self._sim.insert_event(EVENTS.TASK_UPDATE, self._sim.now, lambda: self.check_time_slice())

    def on_task_finish(self, transition, resource):
        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return

        if hw_resource.get_attribute(self.TIME_SLICE) is not None:
            self.finish_round_robin(transition, resource)

        self._sim.insert_event(EVENTS.TASK_UPDATE, self._sim.now, lambda: self.check_time_slice())

    def execute_round_robin(self, transition, resource_type, round_robin_start_time=None):
        """
        Inserts the transition to the waiting list on the resource, and then initiates the round robin process
        for the first task in the list (if it's not initiated yet).
        :param transition:
        :param resource_type:
        :param round_robin_start_time:
        :return:
        """
        task = self._get_task(transition)
        task.attach_attribute(AnalysisExtension.DONT_UPDATE, True)
        resource = self._get_resource(resource_type)
        running_transitions = resource.get_attribute(self.RUNNING_TRANSITIONS, list())
        if task.get_attribute(TaskMetaData.TASK_RUNTIME, 0) == 0:
            resource_type.executing = running_transitions[0] if running_transitions else None
            return

        # Adding the transition to the running list
        running_transitions.append(transition)
        resource.attach_attribute(self.RUNNING_TRANSITIONS, running_transitions)

        time_slice = resource.get_attribute(self.TIME_SLICE)
        if time_slice is None:
            raise ValueError('Resource that uses round robin must define TIME_SLICE attribute')

        resource_type.state = TransitionState.EXECUTING
        if len(running_transitions) == 1:
            running_transition = running_transitions[0]
            running_task = self._get_task(running_transition)
            self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, resource, running_task, True)
            resource_type.executing = running_transition
            # print('start:', str(running_transition.transition.id), str(self._sim.now))
            running_task.attach_attribute(self.TASK_START_TIME, self._sim.now)
            running_task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, None)
            running_task.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
            running_task.attach_attribute(self.DONT_ADD, False)
            running_task.attach_attribute(self.ROUND_ROBIN_START_TIME, self._sim.now)
            running_transition.start_time = self._sim.now
            resource.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
            self._sim.emit(EVENTS.TASK_UPDATE, None)

        # if the resource is not in a round robin process and there are more than 1 transitions running
        # it initiates the round robin process
        else:
            # initiates the next transition and sets it to finish in time_slice or it's finish time
            # (the sooner between them)
            self.handle_running_transition(running_transitions[0], resource_type, time_slice, round_robin_start_time)

            # Adds the time slices of the other waiting tasks to the end event of the task that was currently added
            self.handle_waiting_transition(transition, running_transitions, time_slice)

    def finish_round_robin(self, transition, resource_type):
        """
        End of the time slice, may be initiated by end event of the task, if that happens we need to fix the waiting
        times for the waiting tasks because it could be that the tasks was in the middle of a time slice and was
        finished prematuraly
        :param transition:
        :param resource_type:
        :return:
        """
        # print('finish:', str(transition.transition.id), str(self._sim.now))
        resource = self._get_resource(resource_type)
        running_transitions = resource.get_attribute(self.RUNNING_TRANSITIONS) or list()
        task = self._get_task(transition)
        if task.get_attribute(TaskMetaData.TASK_RUNTIME) == 0:
            resource_type.executing = running_transitions[0] if running_transitions else None
            return

        finished_transition = running_transitions.pop(0)
        if finished_transition != transition:
            raise ValueError('The finished transition was a waiting transition! this shouldn\'t happen at all!')
        resource.attach_attribute(self.RUNNING_TRANSITIONS, running_transitions)
        task.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
        finished_task_start_time = task.get_attribute(self.ROUND_ROBIN_START_TIME)
        if finished_task_start_time is None:
            finished_task_start_time = transition.start_time

        # checks if the task has finished all of it's runtime (which means it was finished by the simulation)
        if transition.end_event.clock == self._sim.now:
            # if it was initated by the time slice instead of the end event we want to wait for the end event
            if transition.end_event in self._sim.get_events():
                running_transitions.insert(0, finished_transition)
                resource.attach_attribute(self.RUNNING_TRANSITIONS, running_transitions)
                return

            self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, resource, task, False)
            # print('total finish:', str(transition.transition.id), str(self._sim.now))
            time_slice = resource.get_attribute(self.TIME_SLICE)
            finish_round_robin_event = task.get_attribute(self.RR_TIME_SLICE_FINISH_EVENT)
            time_add_diff = finished_task_start_time + time_slice - self._sim.now
            task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, None)
            task.attach_attribute(ACTIVE_RUNTIME, 0)
            # The task ended premturaly so we need to get all the end events early by the difference
            self._sim.cancel_event(finish_round_robin_event)
            if len(running_transitions) == 1:
                resource.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
            if running_transitions:
                for waiting_tr in running_transitions:
                    waiting_task = self._get_task(waiting_tr)
                    # print('Fixing delay for task ', waiting_tr.transition.id, ' with', -time_add_diff)
                    change_target_event = waiting_task.get_attribute(MultiMemoryExtension.CHANGE_TARGET_EVENT)
                    if change_target_event is not None:
                        change_target_event.clock -= time_add_diff
                        self._sim.update_event(change_target_event)
                    waiting_tr.end_event.clock -= time_add_diff
                    self._sim.update_event(waiting_tr.end_event)

                last_transition = running_transitions.pop(-1)
                last_task = self._get_task(last_transition)
                # Don't add attribute which tells the round robin algo to not update the end event clock
                last_task.attach_attribute(self.DONT_ADD, True)
                self._sim.insert_event(EVENTS.TASK_EXECUTE, self._sim.now,
                                       lambda: self.execute_round_robin(last_transition, resource_type))
            return

        task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, None)

        self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, resource, task, False)
        self._sim._sim_events.append(SimEvent(
            START=transition.start_time,
            FINISH=self._sim.now,
            TRANSITION=transition.transition.id,
            RESOURCE=resource.ip.name + '/' + resource.name,
            RESOURCE_IDX=0,
            DURATION=self._sim.now - transition.start_time
        ))

        overall_runtime = task.get_attribute(ACTIVE_RUNTIME, 0)
        overall_runtime += self._sim.now - transition.start_time
        task.attach_attribute(ACTIVE_RUNTIME, overall_runtime)

        self._sim.insert_event(EVENTS.TASK_EXECUTE, self._sim.now,
                               lambda: self.execute_round_robin(transition, resource_type))

    def fix_end_event(self, transition, time_to_add):
        """
        Adds time to the end event of the transition
        :param transition:
        :param time_to_add: the time to add
        """
        transition.end_event.clock += time_to_add
        self._sim.update_event(transition.end_event)

    def check_time_slice(self, transition=None):
        """
        Checks if there's an executing transition in the simulation that it's remaining time is bigger than it's
        time slice
        :param: transition: for the event, we're not using it at all
        :return:
        """
        if transition is None:
            return
        for resource_type in list(self._sim.get_resources()):
            resource = self._get_resource(resource_type)
            if resource.get_attribute(self.TIME_SLICE) is None:
                continue
            running_transitions = resource.get_attribute(self.RUNNING_TRANSITIONS, list())
            if len(running_transitions) > 1:
                time_slice = resource.get_attribute(self.TIME_SLICE)
                running_transition = running_transitions[0]
                running_task = self._get_task(running_transition)
                round_robin_event = running_task.get_attribute(self.RR_TIME_SLICE_FINISH_EVENT)
                if round_robin_event is None and \
                        running_transition.end_event.clock - running_task.get_attribute(self.ROUND_ROBIN_START_TIME) > \
                        time_slice:
                    last_transition = running_transitions.pop(-1)
                    last_task = self._get_task(last_transition)
                    last_task.attach_attribute(self.DONT_ADD, True)
                    running_task.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
                    resource.attach_attribute(self.ROUND_ROBIN_PROCESS, False)
                    self.execute_round_robin(last_transition, resource_type,
                                             running_task.get_attribute(self.ROUND_ROBIN_START_TIME))

    def handle_running_transition(self, running_transition, resource_type, time_slice, round_robin_start_time=None):
        """
        Handles the running transition in the resource a waiting task executed on the resource,
        starting a round robin time slice event if it's left runtime is bigger the time slice
        :param running_transition:
        :param resource_type:
        :param time_slice
        :param round_robin_start_time:
        """
        resource_type.executing = running_transition
        resource = self._get_resource(resource_type)
        running_task = self._get_task(running_transition)
        is_running_task_round_robin = running_task.get_attribute(self.ROUND_ROBIN_PROCESS, False)
        is_resource_round_robin = resource.get_attribute(self.ROUND_ROBIN_PROCESS, False)
        if not is_running_task_round_robin:
            if is_resource_round_robin:
                # here the task is starting new round robin slice
                running_task.attach_attribute(self.TASK_START_TIME, self._sim.now)
                running_transition.start_time = self._sim.now
                self._sim.emit(AnalysisExtension.ANALYSIS_EVENT, resource, running_task, True)
                # print('start:', str(running_transition.transition.id), str(self._sim.now))
            else:
                # here the task already ran and then starts the slice
                resource.attach_attribute(self.ROUND_ROBIN_PROCESS, True)
            # need to update the system because a new transition is running
            round_robin_start_time = self._sim.now if round_robin_start_time is None else round_robin_start_time
            running_task.attach_attribute(self.ROUND_ROBIN_START_TIME, round_robin_start_time)
            running_task.attach_attribute(self.ROUND_ROBIN_PROCESS, True)
            self._sim.emit(EVENTS.TASK_UPDATE, None)
            end_event = running_transition.end_event
            task_total_runtime = running_transition.runtime
            task_remaining_time = end_event.clock - round_robin_start_time if end_event is not None else \
                task_total_runtime
            if task_remaining_time > time_slice:
                event = self._sim.insert_event(self.RR_TIME_SLICE_FINISH_EVENT, round_robin_start_time + time_slice,
                                               lambda: self.on_task_finish(running_transition, resource_type))
                running_task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, event)
            else:
                running_task.attach_attribute(self.RR_TIME_SLICE_FINISH_EVENT, None)
        else:
            self._sim.emit(EVENTS.TASK_UPDATE, None)

    def handle_waiting_transition(self, waiting_transition, running_transitions, time_slice):
        """
        Delays the waiting transition by all of the transitions that is ahead in the queue
        :param waiting_transition: waiting_transition
        :param running_transitions: running_transitions list
        :param time_slice:
        :return:
        """
        waiting_task = self._get_task(waiting_transition)
        running_task = self._get_task(running_transitions[0])
        dont_add = waiting_task.get_attribute(self.DONT_ADD, False)
        if not dont_add:
            time_to_add_by_waiting = time_slice * (len(running_transitions) - 2)
            running_task_ran_time = self._sim.now - running_task.get_attribute(self.ROUND_ROBIN_START_TIME)
            time_to_add_by_running = time_slice - running_task_ran_time
            time_to_add = time_to_add_by_running + time_to_add_by_waiting
            Logger.log(self._sim.now,
                       'RoundRobinExtension, delaying by : ' + str(time_to_add) + ' | task: ' +
                       waiting_transition.transition.id)
            change_target_event = waiting_task.get_attribute(MultiMemoryExtension.CHANGE_TARGET_EVENT)
            if change_target_event is not None:
                change_target_event.clock += time_to_add
                self._sim.update_event(change_target_event)
            if waiting_transition.end_event is not None:
                waiting_transition.end_event.clock += time_to_add
                self._sim.update_event(waiting_transition.end_event)
            else:
                end_event_fix = self._sim.insert_event(self.END_EVENT_FIX_EVENT, self._sim.now,
                                                       lambda: self.fix_end_event(waiting_transition, time_to_add))
                waiting_task.attach_attribute(self.END_EVENT_FIX_EVENT, end_event_fix)
        else:
            waiting_task.attach_attribute(self.DONT_ADD, False)
