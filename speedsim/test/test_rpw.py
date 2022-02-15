import os
import unittest

import pandas

from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.utils import create_rpw_task, from_pnml_file, load_platform
from speedsim import SpeedSim


class TestRPW(unittest.TestCase):
    def test_rpw_creation(self):
        """
        Tests the creation of read -> process -> write workload tasks
        """
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        rpw_file = os.path.join(tests, 'input/test_rpw.pnml')
        hw = {'CPU': {'resource': sys_platform.get_ip('ip')}}
        tasks_att = [{'hw_resource': {'values': ['CPU'], 'function_data': {'function': create_rpw_task}}}]
        wl, mapping = from_pnml_file(rpw_file, hw_resources=hw, tasks_att=tasks_att)

        sim = SpeedSim(sys_platform, wl, mapping)

        expected = pandas.DataFrame(data=[
            (0.0, 10.0, '10/trigger_out_start', 'NULL', 0, 10.0),
            (10.0, 10.0, '11/task1/read', 'ip/d', 0, 0.0),
            (10.0, 110.0, '11/task1/process', 'ip/exec_u', 0, 100.0),
            (110.0, 110.0, '11/task1/write', 'ip/d', 0, 0.0),
            (110.0, 110.0, '12/task2/read', 'ip/d', 0, 0.0),
            (110.0, 210.0, '12/task2/process', 'ip/exec_u', 0, 100.0),
            (210.0, 210.0, '12/task2/write', 'ip/d', 0, 0.0),
            (210.0, 210.0, '13/task3/read', 'ip/d', 0, 0.0),
            (210.0, 310.0, '13/task3/process', 'ip/exec_u', 0, 100.0),
            (310.0, 310.0, '13/task3/write', 'ip/d', 0, 0.0),
            (310.0, 310.0, '14/task4/read', 'ip/d', 0, 0.0),
            (310.0, 410.0, '14/task4/process', 'ip/exec_u', 0, 100.0),
            (410.0, 410.0, '14/task4/write', 'ip/d', 0, 0.0),
            (410.0, 410.0, '15/task5/read', 'ip/d', 0, 0.0),
            (410.0, 510.0, '15/task5/process', 'ip/exec_u', 0, 100.0),
            (510.0, 510.0, '15/task5/write', 'ip/d', 0, 0.0),
            (510.0, 520.0, '16/trigger_in_end', 'NULL', 0, 10.0)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])
        events = sim.simulate(5000000)

        pandas.testing.assert_frame_equal(events, expected)

    def test_rpw_with_specific_mappings(self):
        """
        Tests the creation of read -> process -> write workload tasks with specific mappings in the custom function
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

        gt = IP("gt", clk, [gt_ex], [gt_dr], [gt_p])
        gt.connect_driver(gt_dr, gt_p)
        sys_platform.add_ip(gt)

        sys_platform.connect_to_bus(gt_p, sys_platform.get_bus('bus1'))

        sys_platform.validate_platform()

        def create_rpw_task_with_mapping(transition, reference_freq):
            task = create_rpw_task(transition, reference_freq)
            workload = task.workload
            mapping = task.mapping
            read = workload.get_task('read')
            proc = workload.get_task('process')
            write = workload.get_task('write')
            mapping.map_task(read, sys_platform.get_ip('ip'))
            mapping.map_task(proc,  sys_platform.get_ip('ip'))
            mapping.map_task(write, gt)
            return task

        rpw_file = os.path.join(tests, 'input/test_rpw.pnml')
        hw = {'CPU': {'resource': sys_platform.get_ip('ip')}}
        tasks_att = [{'hw_resource': {'values': ['CPU'], 'function': create_rpw_task_with_mapping}}]
        wl, mapping = from_pnml_file(rpw_file, hw_resources=hw, tasks_att=tasks_att)

        sim = SpeedSim(sys_platform, wl, mapping)
        events = sim.simulate(500000000)

        filter_read_tasks = events[events['TRANSITION'].str.endswith('read')]
        self.assertFalse(any(filter_read_tasks.RESOURCE == 'gt/gt_dr'))

        filter_write_tasks = events[events['TRANSITION'].str.endswith('write')]
        self.assertFalse(any(filter_write_tasks.RESOURCE == 'ip/d'))
        self.assertFalse(any(filter_write_tasks.RESOURCE == 'ip/exec_u'))
