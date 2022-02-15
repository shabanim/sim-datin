"""
Extensions for validating simulation values in run time
"""
from asap.strings import RESOURCE, TASK
from asap.workload import TYPES, TaskMetaData
from pnets.simulation import EVENTS
from speedsim_utils import Logger


class TaskRuntimeValidator:
    """
    Task runtime validator is for controlling simulation behavior according to tasks run time.
    In this case, checks task right before execution:
        - if task runtime > threshold: continue normally
        - if task runtime < threshold:
            - if padding is true: add to task runtime
            - else: kill simulation
    """

    def __init__(self, sim, system_mgr):
        self._sim = sim
        self._system_mgr = system_mgr
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self._on_task_execute)
        self._threshold = 0
        self._padding = True
        self._delta = 0

    def _get_task(self, transition):
        """
        Getting task of speedSim transition
        :param transition:
        :return: Task
        """
        return transition.get_pnml_attribute(TASK)

    def _handle_task(self, transition):
        """
        Handles the task by updating the speedsim Transition runtime according to it
        :param transition:
        :return:
        """
        transition.runtime = self._get_task(transition).get_attribute(TaskMetaData.TASK_RUNTIME)

    def _get_resource(self, resource):
        """
        Getting platform resource out of speedsim resource
        :param resource:
        :return:
        """
        if resource is None or resource.resource_type == 'NULL':
            return None
        return resource.get_attribute(RESOURCE)

    def _is_zero_duration_task(self, task):
        """
        Checks if the task runtime is lower than threshold
        :param task:
        :return:
        """
        return (task.type == TYPES.READ and task.read_bytes == 0) or \
               (task.type == TYPES.WRITE and task.write_bytes == 0) or \
               ((task.type == TYPES.PROC or task.type == TYPES.GEN) and task.processing_cycles == 0)

    def _on_task_execute(self, transition, resource):

        task = self._get_task(transition)
        if task is None:
            return

        hw_resource = self._get_resource(resource)
        if hw_resource is None:
            return
        if self._is_zero_duration_task(task):
            task.attach_attribute(TaskMetaData.TASK_RUNTIME, 0)
        else:
            self.validate_task(task)
        self._handle_task(transition)

    def instantiate(self, threshold=0, delta=0, padding=True):
        self._threshold = threshold
        self._delta = delta
        self._padding = padding

    def validate_task(self, task):
        runtime = task.get_attribute(TaskMetaData.TASK_RUNTIME)
        Logger.log('', 'Validating task runtime, task: ' + task.name + ' , runtime: ' + str(runtime))
        if runtime is None:
            raise Exception('Killing simulation! task:', task.name, 'does have any runtime')
        if runtime < self._threshold:
            if self._padding:
                runtime = self._threshold + self._delta
            else:
                raise Exception('Killing simulation! some tasks run time are lower than the threshold:',
                                self._threshold,
                                'for example: ', task.name, ', With runtime:', runtime)
        Logger.log('', 'Validating task runtime, task new runtime: ' + str(runtime))
        task.attach_attribute(TaskMetaData.TASK_RUNTIME, runtime)
