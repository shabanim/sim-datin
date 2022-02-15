import os
import unittest

import pandas

from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.mapping import Mapping
from asap.utils import load_platform
from asap.workload import TYPES, Task, WlTask, Workload
from models.fabric.abstract_fabric import FabricExtension
from speedsim import SpeedSim


class TestSplit(unittest.TestCase):
    def test_process_split(self):
        """
        Tests data split on processing tasks
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # GT
        clk = sys_platform.get_clock('clk')
        gt_p = Port('gt_p')
        gt_dr = Driver('gt_dr', clk)
        gt_ex = ExecutingUnit('gt_ex_u', clk)

        gt = IP("GT", clk, [gt_ex], [gt_dr], [gt_p])
        gt.connect_driver(gt_dr, gt_p)
        sys_platform.add_ip(gt)

        sys_platform.connect_to_bus(gt_p, sys_platform.get_bus('bus1'))

        sys_platform.validate_platform()

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', TYPES.PROC, processing_cycles=1000)
        task2 = Task('task2', TYPES.PROC, processing_cycles=1000)
        internal_wl = Workload('internal_wl', [start, task1, task2, end])
        internal_mapping = Mapping('internal_m', internal_wl)

        internal_mapping.map_task(task1, gt)
        internal_mapping.map_task(task2, sys_platform.get_ip('ip'))

        internal_wl.connect_tasks('1', start, task1)
        internal_wl.connect_tasks('2', task1, task2)
        internal_wl.connect_tasks('3', task2, end)

        main_task = WlTask('main_task', internal_wl, internal_mapping, 5)
        wl = Workload('wl', [start, end, main_task])
        m = Mapping('m', wl)

        wl.connect_tasks('1', start, main_task)
        wl.connect_tasks('2', main_task, end)

        speedsim = SpeedSim(sys_platform, wl, m)

        res = speedsim.simulate(1000000)

        expected = pandas.DataFrame(data=[
            (0, 2, 'main_task/task1', 'GT/gt_ex_u', 0, 2),
            (2, 4, 'main_task/task2', 'ip/exec_u', 0, 2),
            (2, 4, 'main_task/task1', 'GT/gt_ex_u', 0, 2),
            (4, 6, 'main_task/task2', 'ip/exec_u', 0, 2),
            (4, 6, 'main_task/task1', 'GT/gt_ex_u', 0, 2),
            (6, 8, 'main_task/task2', 'ip/exec_u', 0, 2),
            (6, 8, 'main_task/task1', 'GT/gt_ex_u', 0, 2),
            (8, 10, 'main_task/task2', 'ip/exec_u', 0, 2),
            (8, 10, 'main_task/task1', 'GT/gt_ex_u', 0, 2),
            (10, 12, 'main_task/task2', 'ip/exec_u', 0, 2)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected, check_dtype=False)

    def test_process_data(self):
        """
        Tests data split on read and write tasks
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # GT
        clk = sys_platform.get_clock('clk')
        gt_p = Port('gt_p')
        gt_dr = Driver('gt_dr', clk)
        gt_ex = ExecutingUnit('gt_ex_u', clk)

        gt = IP("GT", clk, [gt_ex], [gt_dr], [gt_p])
        gt.connect_driver(gt_dr, gt_p)
        sys_platform.add_ip(gt)

        sys_platform.connect_to_bus(gt_p, sys_platform.get_bus('bus1'))

        sys_platform.validate_platform()

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', TYPES.READ, read_bytes=10000)
        task2 = Task('task2', TYPES.WRITE, write_bytes=10000)
        internal_wl = Workload('internal_wl', [start, task1, task2, end])
        internal_mapping = Mapping('internal_m', internal_wl)

        internal_mapping.map_task(task1, gt)
        internal_mapping.map_task(task2, sys_platform.get_ip('ip'))

        internal_wl.connect_tasks('1', start, task1)
        internal_wl.connect_tasks('2', task1, task2)
        internal_wl.connect_tasks('3', task2, end)

        main_task1 = WlTask('main_task1', internal_wl, internal_mapping, 2)
        main_task2 = WlTask('main_task2', internal_wl, internal_mapping, 2)
        wl = Workload('wl', [start, end, main_task1, main_task2])
        m = Mapping('m', wl)

        wl.connect_tasks('1', start, main_task1)
        wl.connect_tasks('2', main_task1, main_task2)
        wl.connect_tasks('3', main_task2, end)

        speedsim = SpeedSim(sys_platform, wl, m)
        speedsim.add_extension('Fabric_extension', FabricExtension)

        res = speedsim.simulate(1000000)

        expected = pandas.DataFrame(data=[
            (0.0, 0.78125, 'main_task1/task1', 'GT/gt_dr', 0, 0.78125),
            (0.78125, 2.34375, 'main_task1/task2', 'ip/d', 0, 1.56250),
            (0.78125, 2.34375, 'main_task1/task1', 'GT/gt_dr', 0, 1.56250),
            (2.34375, 3.12500, 'main_task1/task2', 'ip/d', 0, 0.78125),
            (3.12500, 3.90625, 'main_task2/task1', 'GT/gt_dr', 0, 0.78125),
            (3.90625, 5.46875, 'main_task2/task2', 'ip/d', 0, 1.56250),
            (3.90625, 5.46875, 'main_task2/task1', 'GT/gt_dr', 0, 1.56250),
            (5.46875, 6.25000, 'main_task2/task2', 'ip/d', 0, 0.78125)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected)

    def test_complex_split(self):
        """
        Tests complex structure with put_samples and get_samples that are larger than 1
        + connecting normal task to workload task
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', TYPES.PROC, processing_cycles=100)
        task2 = Task('task2', TYPES.PROC, processing_cycles=200)
        task3 = Task('task3', TYPES.PROC, processing_cycles=150)
        second_wl = Workload('second_wl', [start, end, task1, task2, task3])
        second_m = Mapping('second_m', second_wl)

        second_wl.connect_tasks('1', start, task1)
        second_wl.connect_tasks('2', task1, task2)
        second_wl.connect_tasks('3', task1, task3)
        second_wl.connect_tasks('4', task2, end)
        second_wl.connect_tasks('5', task3, end)

        second_m.map_task(task1, sys_platform.get_ip('ip'))
        second_m.map_task(task2, sys_platform.get_ip('ip'))
        second_m.map_task(task3, sys_platform.get_ip('ip'))

        main_start = Task('main_start', TYPES.START)
        main_end = Task('main_end', TYPES.END)
        main_task1 = WlTask('main_task1', second_wl, second_m, 5)
        main_task2 = WlTask('main_task2', second_wl, second_m, 2)
        main_task3 = WlTask('main_task3', second_wl, second_m, 10)
        normal_task = Task('normal_task', TYPES.GEN, processing_cycles=100)

        wl = Workload('wl', [main_start, main_end, main_task1, main_task2, main_task3, normal_task])
        m = Mapping('m', wl)

        wl.connect_tasks('1', main_start, main_task1, put_samples=2, buf_size=2)
        wl.connect_tasks('2', main_task1, main_task2)
        wl.connect_tasks('3', main_task1, main_task3)
        wl.connect_tasks('4', main_task2, normal_task, get_samples=2, buf_size=2)
        wl.connect_tasks('5', main_task3, normal_task, get_samples=2, buf_size=2)
        wl.connect_tasks('6', normal_task, main_end)

        speedsim = SpeedSim(sys_platform, wl, m)

        res = speedsim.simulate()

        self.assertEqual(res['TRANSITION'].eq('main_task1/task2').sum(), 10)
        self.assertEqual(res['TRANSITION'].eq('main_task3/task3').sum(), 20)
        self.assertEqual(res['TRANSITION'].eq('main_task2/task1').sum(), 4)
        self.assertEqual(res['TRANSITION'].eq('normal_task').sum(), 1)
