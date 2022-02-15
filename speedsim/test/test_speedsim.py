import os
import tempfile
import unittest

import pandas
from pandas.testing import assert_frame_equal

from asap.mapping import Mapping
from asap.utils import load_platform
from asap.workload import TYPES, Task, Workload
from speedsim import SpeedSim


class TestSpeedSim(unittest.TestCase):
    def test_speedsim(self):
        """
        Tests Speed Sim - simple platform, simple workload, simple mapping
            - Platform - 1 Clock, 1 Ip, 1 Memory, 1 Bus
            - workload - 5 serial tasks
        Checks if the results are the same as predicted
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        wl = Workload('wl')
        m = Mapping('mapping', wl)

        start = Task('start', TYPES.START)
        wl.add_task(start)
        prev = start
        for i in range(1, 6):
            task = Task('task'+str(i), processing_cycles=10)
            wl.add_task(task)
            wl.connect_tasks(str(i), prev, task)
            m.map_task(task, sys_platform.get_ip('ip'))
            prev = task

        end = Task('end', TYPES.END)
        wl.add_task(end)
        wl.connect_tasks(6, prev, end)

        sim = SpeedSim(sys_platform, wl, m)
        expected = pandas.DataFrame(data=[
            (0.0, 0.1, 'task1', 'ip/exec_u', 0, 0.1),
            (0.1, 0.2, 'task2', 'ip/exec_u', 0, 0.1),
            (0.2, 0.30000000000000004, 'task3', 'ip/exec_u', 0, 0.10000000000000003),
            (0.30000000000000004, 0.4, 'task4', 'ip/exec_u', 0, 0.09999999999999998),
            (0.4, 0.5, 'task5', 'ip/exec_u', 0, 0.09999999999999998)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])
        events = sim.simulate(5000000)

        assert_frame_equal(events, expected)

    def test_speedsim_with_json(self):
        """
        Tests Speed Sim - complicated platform, workload and mapping
            - Platform - 1 Clock, 2 Ips (3 Drivers, 2 executing units, 2 Ports), 1 Bus, 1 Memory
            - Workload - 8 complex tasks
        Checks if the results of the simulation before json and after json are the same
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/complex_platform.json')
        sys_platform = load_platform(file)

        # Workload
        wl = Workload('wl')
        m = Mapping('mapping', wl)

        start = Task('start', TYPES.START)
        for i in range(1, 9):
            wl.add_task(Task('task' + str(i), processing_cycles=i*10))
        end = Task('end', TYPES.END)

        wl.add_task(start)
        wl.add_task(end)

        wl.connect_tasks('1', start, wl.get_task('task1'))
        wl.connect_tasks('2', wl.get_task('task1'), wl.get_task('task2'))
        for i in range(3, 6):
            wl.connect_tasks(str(i), wl.get_task('task2'), wl.get_task('task'+str(i)))
        wl.connect_tasks('6', wl.get_task('task3'), wl.get_task('task6'))
        wl.connect_tasks('7', wl.get_task('task3'), wl.get_task('task7'))
        wl.connect_tasks('8', wl.get_task('task4'), wl.get_task('task8'))
        for i in range(5, 9):
            wl.connect_tasks(str(i+4), wl.get_task('task'+str(i)), end)

        for i in range(1, 5):
            m.map_task(wl.get_task('task'+str(i)), sys_platform.get_ip('ip1'))
        for i in range(5, 9):
            m.map_task(wl.get_task('task' + str(i)), sys_platform.get_ip('ip2'))

        tmp_path = tempfile.NamedTemporaryFile('w', suffix='.json')
        tmp_path_name = tmp_path.name
        tmp_path.close()
        sys_platform.save(tmp_path_name)

        json_sys = load_platform(tmp_path_name)

        sim1 = SpeedSim(sys_platform, wl, m)
        sim2 = SpeedSim(json_sys, wl, m)
        res1 = sim1.simulate(5000000)
        res2 = sim2.simulate(5000000)

        pandas.testing.assert_frame_equal(res1, res2)
