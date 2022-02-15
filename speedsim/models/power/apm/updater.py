import os
import sys

from strings import NEMO_PATH, SC_PACKAGE

sc_package = os.environ[SC_PACKAGE]
if sc_package not in sys.path:
    sys.path.append(sc_package)

nemo_path = os.environ[NEMO_PATH]
if nemo_path not in sys.path:
    sys.path.append(nemo_path)

from apm_lib import BaseUpdater  # isort:skip # noqa: E402
from sc import sc_time_stamp  # isort:skip # noqa: E402


class Updater(BaseUpdater):
    def __init__(self, *args, **kwargs):
        BaseUpdater.__init__(self, *args, **kwargs)
        self._updates = 0
        self._apm = None
        if 'apm' in kwargs:
            self._apm = kwargs['apm']

    @staticmethod
    def get_time():
        return sc_time_stamp().to_seconds() * 1e6

    def update(self, module, residency, window_residency):
        """
        Updates frequency of module according to total residency and window residency
        :param module: Module name in APM
        :param residency: Total residency till now
        :param window_residency:
        :return: frequency in MHz
        """
        try:
            self._updates = self._updates + 1
            # if self._apm is not None and self._apm.resources.get(module) is not None:
            # here you can access previous period (convert to frequency) as demonstrated below
            # old_period = self._apm.resources[module].get_attribute(RESOURCE).clock.period
            # print('Updating module:', module, ', with total residency:', residency, ', and window residency:',
            #       window_residency, ', on time', self.get_time())
            # new_freq = int(int(residency * 50) * 100 + 1000)
            # listener = self.get_listener()
            # listener.direct_update_frequency(module, new_freq)
        except Exception as e:
            print(e)
        return
