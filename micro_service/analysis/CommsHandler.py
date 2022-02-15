from asap.extensions import BaseRunTime
from pnets.simulation import EVENTS

class CommsHandler(BaseRunTime):
    """

    """
    def __init__(self, sim, system_mgr):
        super().__init__(sim, system_mgr)
        self._sim.connect_to_event(EVENTS.TASK_EXECUTE, self._on_task_execute)

    def _on_task_execute(self, transition, resource):
        print("_on_task_execute invoked")
