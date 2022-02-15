import os
import unittest

import pandas

from asap.hw import GlobalClock
from asap.ips import ExecutingUnit
from asap.mapping import Mapping
from asap.utils import load_platform
from asap.workload import TYPES, Task, WlTask, Workload
from speedsim import SpeedSim


class TestHierarchicalWorkloads(unittest.TestCase):
    def test_hierarchical_workloads_two_levels(self):
        """
        Checks the hierarchical workloads option with Speedsim
        2 levels simple workload
        """
        # simple platform for the test
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # workloads
        test_wl = Workload('test')
        test_m = Mapping('test_m', test_wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        test = Task('internal_task', processing_cycles=30)

        test_wl.add_task(start)
        test_wl.add_task(end)
        test_wl.add_task(test)
        test_wl.connect_tasks('1', start, test)
        test_wl.connect_tasks('2', test, end)

        # The main workload
        wl = Workload('wl')
        m = Mapping('mapping', wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        wl_task = WlTask('wl_task', test_wl, test_m)

        wl.add_task(start)
        wl.add_task(end)
        wl.add_task(wl_task)
        wl.connect_tasks('3', start, wl_task)
        wl.connect_tasks('4', wl_task, end)

        test_m.map_task(test, sys_platform.get_ip('ip'))

        sim = SpeedSim(sys_platform, wl, m)

        expected = pandas.DataFrame(data=[
            (0.0, 0.3, 'wl_task/internal_task', 'ip/exec_u', 0, 0.3)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.simulate(500000)

        pandas.testing.assert_frame_equal(events, expected)

    def test_hierarchical_workloads_three_levels(self):
        """
        Checks the hierarchical workloads option with Speedsim
        3 levels simple workload
        """
        # simple platform for the test
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # Workloads

        # third level workload
        third_wl = Workload('third_wl')
        third_mapping = Mapping('third_mapping', third_wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        internal_task = Task('internal_task', processing_cycles=30)

        third_wl.add_task(start)
        third_wl.add_task(end)
        third_wl.add_task(internal_task)
        third_wl.connect_tasks('1', start, internal_task)
        third_wl.connect_tasks('2', internal_task, end)

        third_mapping.map_task(internal_task, sys_platform.get_ip('ip'))

        # second level workload
        second_wl = Workload('second_wl')
        second_mapping = Mapping('second_mapping', second_wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        third_wl_task = WlTask('third_wl_task', third_wl, third_mapping)

        second_wl.add_task(start)
        second_wl.add_task(end)
        second_wl.add_task(third_wl_task)
        second_wl.connect_tasks('1', start, third_wl_task)
        second_wl.connect_tasks('2', third_wl_task, end)

        # The main workload
        wl = Workload('wl')
        m = Mapping('mapping', wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        wl_task = WlTask('second_wl_task', second_wl, second_mapping)

        wl.add_task(start)
        wl.add_task(end)
        wl.add_task(wl_task)
        wl.connect_tasks('3', start, wl_task)
        wl.connect_tasks('4', wl_task, end)

        sim = SpeedSim(sys_platform, wl, m)

        expected = pandas.DataFrame(data=[
            (0.0, 0.3, 'second_wl_task/third_wl_task/internal_task', 'ip/exec_u', 0, 0.3)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.simulate(500000)

        pandas.testing.assert_frame_equal(events, expected)

    def test_hierarchical_workloads_complex(self):
        """
        Checks the hierarchical workloads option with Speedsim
        3 levels complex workload
        """
        # simple platform for the test
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # Workloads
        # third level workload
        third_wl = Workload('third_wl')
        third_mapping = Mapping('third_mapping', third_wl)

        start = Task('start', TYPES.START)
        end1 = Task('end1', TYPES.END)
        end2 = Task('end2', TYPES.END)
        for i in range(5, 8):
            task = Task('task' + str(i), processing_cycles=10)
            third_wl.add_task(task)
            third_mapping.map_task(task, sys_platform.get_ip('ip'))
        third_wl.add_task(end1)
        third_wl.add_task(end2)
        third_wl.connect_tasks('1', start, third_wl.get_task('task5'))
        third_wl.connect_tasks('2', third_wl.get_task('task5'), third_wl.get_task('task6'))
        third_wl.connect_tasks('3', third_wl.get_task('task5'), third_wl.get_task('task7'))
        third_wl.connect_tasks('4', third_wl.get_task('task6'), end1)
        third_wl.connect_tasks('5', third_wl.get_task('task7'), end2)

        # second level workload
        second_wl = Workload('second_wl')
        second_mapping = Mapping('second_mapping', second_wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)

        for i in range(3, 5):
            task = Task('task' + str(i), processing_cycles=10)
            second_wl.add_task(task)
            second_mapping.map_task(task, sys_platform.get_ip('ip'))
        third_wl_task = WlTask('third_wl_task', third_wl, third_mapping)

        second_wl.add_task(start)
        second_wl.add_task(end)
        second_wl.add_task(third_wl_task)
        second_wl.connect_tasks('1', start, second_wl.get_task('task3'))
        second_wl.connect_tasks('2', second_wl.get_task('task3'), second_wl.get_task('task4'))
        second_wl.connect_tasks('3', second_wl.get_task('task4'), third_wl_task)
        second_wl.connect_tasks('4', third_wl_task, end)

        # The main workload
        wl = Workload('wl')
        mapping = Mapping('mapping', wl)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        second_wl_task = WlTask('second_wl_task', second_wl, second_mapping)
        task8 = Task('task8', processing_cycles=10)
        for i in range(1, 3):
            task = Task('task' + str(i), processing_cycles=10)
            wl.add_task(task)
            mapping.map_task(task, sys_platform.get_ip('ip'))
        wl.add_task(start)
        wl.add_task(end)
        wl.add_task(second_wl_task)
        wl.add_task(task8)
        mapping.map_task(task8, sys_platform.get_ip('ip'))
        wl.connect_tasks('1', start, second_wl_task)
        wl.connect_tasks('2', start, wl.get_task('task1'))
        wl.connect_tasks('3', start, wl.get_task('task2'))
        wl.connect_tasks('4', wl.get_task('task2'), task8)
        wl.connect_tasks('5', task8, end)
        wl.connect_tasks('6', wl.get_task('task1'), end)
        wl.connect_tasks('7', second_wl_task, end)

        sim = SpeedSim(sys_platform, wl, mapping)

        expected = pandas.DataFrame(data=[
            (0.0, 0.1, 'task1', 'ip/exec_u', 0, 0.1),
            (0.1, 0.2, 'task2', 'ip/exec_u', 0, 0.1),
            (0.2, 0.3, 'second_wl_task/task3', 'ip/exec_u', 0, 0.1),
            (0.3, 0.4, 'task8', 'ip/exec_u', 0, 0.1),
            (0.4, 0.5, 'second_wl_task/task4', 'ip/exec_u', 0, 0.1),
            (0.5, 0.6, 'second_wl_task/third_wl_task/task5', 'ip/exec_u', 0, 0.1),
            (0.6, 0.7, 'second_wl_task/third_wl_task/task6', 'ip/exec_u', 0, 0.1),
            (0.7, 0.8, 'second_wl_task/third_wl_task/task7', 'ip/exec_u', 0, 0.1)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.simulate(500000)

        pandas.testing.assert_frame_equal(events, expected)

    def test_multiple_hierarchical_workloads(self):
        """
        Checks multiple use of the same workload
        """
        # simple platform for the test
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        second_eu = ExecutingUnit('second_exec_u', GlobalClock.instance)
        sys_platform.get_ip('ip').add_executing_unit(second_eu)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        sub_wl = Workload('sub_wl', [start, end])
        sub_m = Mapping('sub_mapping', sub_wl)

        prev = start
        for i in range(1, 4):
            task = Task('task'+str(i), TYPES.GEN, processing_cycles=10)
            sub_wl.add_task(task)
            sub_wl.connect_tasks(str(i), prev, task)
            sub_m.map_task(task, sys_platform.get_ip('ip'))
            prev = task
        sub_wl.connect_tasks('4', prev, end)

        wl = Workload('workload', [start, end])
        m = Mapping('mapping', wl)

        for i in range(1, 4):
            task = WlTask('main_task'+str(i), sub_wl, sub_m)
            wl.add_task(task)
            wl.connect_tasks(str(i), start, task)
            wl.connect_tasks(str(i+3), task, end)

        sim = SpeedSim(sys_platform, wl, m)

        expected = pandas.DataFrame(data=[
            (0.0, 0.1, 'main_task1/task1', 'ip/exec_u', 0, 0.1),
            (0.0, 0.1, 'main_task2/task1', 'ip/second_exec_u', 0, 0.1),
            (0.1, 0.2, 'main_task3/task1', 'ip/exec_u', 0, 0.1),
            (0.1, 0.2, 'main_task1/task2', 'ip/second_exec_u', 0, 0.1),
            (0.2, 0.3, 'main_task2/task2', 'ip/exec_u', 0, 0.1),
            (0.2, 0.3, 'main_task3/task2', 'ip/second_exec_u', 0, 0.1),
            (0.3, 0.4, 'main_task1/task3', 'ip/exec_u', 0, 0.1),
            (0.3, 0.4, 'main_task2/task3', 'ip/second_exec_u', 0, 0.1),
            (0.4, 0.5, 'main_task3/task3', 'ip/exec_u', 0, 0.1)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.simulate(500000)

        pandas.testing.assert_frame_equal(events, expected)
