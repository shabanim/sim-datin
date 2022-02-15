import os
import unittest

import pandas

from asap.mapping import Mapping
from asap.strings import ResourceDesc
from asap.utils import load_platform
from asap.workload import TYPES, Task, Workload
from post_processing.utils import AnalysisData, get_hw_analysis
from speedsim import SpeedSim


class TestAnalysis(unittest.TestCase):
    def test_analysis(self):
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # Workload
        start = Task('start', TYPES.START)
        proc_task = Task('task1', TYPES.PROC, processing_cycles=253)
        read_task = Task('task2', TYPES.READ, read_bytes=100, processing_cycles=43)
        read_task2 = Task('task3', TYPES.READ, processing_cycles=53)
        end = Task('end', TYPES.END)

        wl = Workload('workload', [start, proc_task, read_task, read_task2, end])
        mapping = Mapping('mapping', wl)

        wl.connect_tasks('1', start, proc_task)
        wl.connect_tasks('2', start, read_task)
        wl.connect_tasks('3', proc_task, read_task2)
        wl.connect_tasks('4', read_task2, end)
        wl.connect_tasks('5', read_task, end)

        mapping.map_task(proc_task, sys_platform.get_ip('ip'))
        mapping.map_task(read_task, sys_platform.get_ip('ip'))
        mapping.map_task(read_task2, sys_platform.get_ip('ip'))

        speedsim = SpeedSim(sys_platform, wl, mapping)

        res = speedsim.simulate()  # noqa: F841
        sys_platform.reset()
        speedsim = SpeedSim(sys_platform, wl, mapping)
        res = speedsim.simulate()  # noqa: F841

        ip_table, ip_res = get_hw_analysis(ResourceDesc.IP, intervals=10)
        ip_predicted = pandas.DataFrame(data=[
                    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                    (100, 100, 100, 100, 100, 100, 100, 100, 100.0, 100.0)],
            columns=['0.00-0.25', '0.25-0.51', '0.51-0.76', '0.76-1.01', '1.01-1.27',
                     '1.27-1.52', '1.52-1.77', '1.77-2.02', '2.02-2.28', '2.28-2.53'],
            index=['ip/d', 'ip/exec_u'],
            dtype=float)

        pandas.testing.assert_frame_equal(ip_res, ip_predicted)

        ip_runtime, ip_window = get_hw_analysis(ResourceDesc.IP, start=0.2, end=0.8)
        self.assertEqual(ip_window['0.20-0.80']['ip/d'], 0.0)
        self.assertEqual(ip_window['0.20-0.80']['ip/exec_u'], 100)

        AnalysisData.reset()
        sys_platform.reset()
        speedsim = SpeedSim(sys_platform, wl, mapping)
        res = speedsim.simulate(5)  # noqa: F841

        ip_table, ip_res = get_hw_analysis(ResourceDesc.IP)

        self.assertEqual(ip_table['FINISH'][1], 2.5300000000000002)
