import os
import unittest

import pandas

from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.mapping import Mapping
from asap.strings import AND, OR, TaskMetaData
from asap.utils import load_platform
from asap.workload import TYPES, Task, WlTask, Workload
from models.fabric.abstract_fabric import FabricExtension
from speedsim import SpeedSim


class TestGating(unittest.TestCase):
    def test_simple_gating(self):
        """
        Tests gating attribute for tasks with simple test
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
        task2 = Task('task2', TYPES.PROC, processing_cycles=1500)
        task3 = Task('task3', TYPES.READ, read_bytes=10000)
        task3.attach_attribute(TaskMetaData.GATING, OR)
        wl = Workload('wl', [start, task1, task2, task3, end])
        mapping = Mapping('mapping', wl)

        mapping.map_task(task1, sys_platform.get_ip('ip'))
        mapping.map_task(task2, gt)
        mapping.map_task(task3, gt)

        wl.connect_tasks('start->task1', start, task1)
        wl.connect_tasks('start->task2', start, task2)
        wl.connect_tasks('task2->task3', task2, task3, put_samples=4, get_samples=2, buf_size=4)
        wl.connect_tasks('task1->task3', task1, task3, put_samples=9, get_samples=3, buf_size=9)
        wl.connect_tasks('task3->end', task3, end)

        speedsim = SpeedSim(sys_platform, wl, mapping)

        speedsim.add_extension('FabricExtension', FabricExtension)

        res = speedsim.simulate(1000000)

        expected = pandas.DataFrame(data=[
            (0, 10, 'task1', 'ip/exec_u', 0, 10),
            (10, 11.56250, 'task3', 'GT/gt_dr', 0, 1.56250),
            (11.56250, 13.12500, 'task3', 'GT/gt_dr', 0, 1.56250),
            (13.12500, 14.68750, 'task3', 'GT/gt_dr', 0, 1.56250),
            (0, 15, 'task2', 'GT/gt_ex_u', 0, 15),
            (15, 16.56250, 'task3', 'GT/gt_dr', 0, 1.56250),
            (16.56250, 18.12500, 'task3', 'GT/gt_dr', 0, 1.56250)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected, check_dtype=False)

    def test_complex_gating(self):
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

        # Task 3 is a workload with 2 parallel tasks, one with AND gating and one with OR gating
        task3_start = Task('start', TYPES.START)
        task3_end = Task('end', TYPES.END)
        task3_or = Task('OR', TYPES.READ, read_bytes=64000)
        task3_or.attach_attribute(TaskMetaData.GATING, OR)
        task3_and = Task('AND', TYPES.PROC, processing_cycles=500)
        task3_and.attach_attribute(TaskMetaData.GATING, AND)

        task3_wl = Workload('task3_wl', [task3_and, task3_or, task3_start, task3_end])
        task3_wl.connect_tasks('task3_start->task3_or', task3_start, task3_or)
        task3_wl.connect_tasks('task3_start->task3_and', task3_start, task3_and)
        task3_wl.connect_tasks('task3_or->tasks3_end', task3_or, task3_end)
        task3_wl.connect_tasks('task3_and->tasks3_end', task3_and, task3_end)

        task3_m = Mapping('tasks3_m', task3_wl)
        task3_m.map_task(task3_or, gt)
        task3_m.map_task(task3_and, sys_platform.get_ip('ip'))

        task3 = WlTask('task3', task3_wl, task3_m)
        task3.attach_attribute(TaskMetaData.GATING, OR)

        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', TYPES.PROC, processing_cycles=1000)
        task2 = Task('task2', TYPES.PROC, processing_cycles=1500)
        wl = Workload('wl', [start, task1, task2, task3, end])
        mapping = Mapping('mapping', wl)

        mapping.map_task(task1, sys_platform.get_ip('ip'))
        mapping.map_task(task2, gt)
        mapping.map_task(task3, gt)

        wl.connect_tasks('start->task1', start, task1)
        wl.connect_tasks('start->task2', start, task2)
        wl.connect_tasks('task2->task3', task2, task3, put_samples=4, get_samples=2, buf_size=4)
        wl.connect_tasks('task1->task3', task1, task3, put_samples=9, get_samples=3, buf_size=9)
        wl.connect_tasks('task3->end', task3, end)

        speedsim = SpeedSim(sys_platform, wl, mapping)

        speedsim.add_extension('FabricExtension', FabricExtension)

        res = speedsim.simulate(1000000)

        expected = pandas.DataFrame(data=[
            (0, 10, 'task1', 'ip/exec_u', 0, 10),
            (0, 15, 'task2', 'GT/gt_ex_u', 0, 15),
            (10, 15, 'task3/AND', 'ip/exec_u', 0, 5),
            (10, 20, 'task3/OR', 'GT/gt_dr', 0, 10),
            (20, 25, 'task3/AND', 'ip/exec_u', 0, 5),
            (20, 30, 'task3/OR', 'GT/gt_dr', 0, 10),
            (30, 35, 'task3/AND', 'ip/exec_u', 0, 5),
            (30, 40, 'task3/OR', 'GT/gt_dr', 0, 10),
            (40, 45, 'task3/AND', 'ip/exec_u', 0, 5),
            (40, 50, 'task3/OR', 'GT/gt_dr', 0, 10),
            (50, 55, 'task3/AND', 'ip/exec_u', 0, 5),
            (50, 60, 'task3/OR', 'GT/gt_dr', 0, 10)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected, check_dtype=False)
