import os
import unittest

import pandas

from asap.mapping import Mapping
from asap.schedulers import BlockingScheduler
from asap.utils import load_platform
from asap.workload import TYPES, Task, Workload
from notebooks.MTL.mtl_near_far_fabric import MTLNearFarFabricMemDistribution
from speedsim import SpeedSim


class TestBlocking(unittest.TestCase):
    def test_blocking_scheduler(self):
        """
        Tests the blocking scheduler currect activity
        """

        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/base_platform.json')
        sys_platform = load_platform(file)

        # Workload - task 2 blockes the gt and then task 3 unblockes it
        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', type=TYPES.WRITE, write_bytes=1000000)
        task1.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task2 = Task('task2', type=TYPES.PROC, processing_cycles=500000)
        task2.attach_attribute('MEMORY_TARGETS', {'memory': 100})
        task2.attach_attribute(BlockingScheduler.BLOCKING_TYPE, BlockingScheduler.BLOCKING)
        task2.attach_attribute(BlockingScheduler.BLOCKING_ID, 15)

        task3 = Task('task3', type=TYPES.READ, read_bytes=250000)
        task3.attach_attribute('MEMORY_TARGETS', {'memory': 100})
        task3.attach_attribute(BlockingScheduler.BLOCKING_TYPE, BlockingScheduler.UNBLOCKING)
        task3.attach_attribute(BlockingScheduler.BLOCKING_ID, 15)

        task4 = Task('task4', type=TYPES.READ, read_bytes=125000)
        task4.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task5 = Task('task5', type=TYPES.WRITE, write_bytes=300000)
        task5.attach_attribute('MAP_TYPE', 'GT')
        task5.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        workload = Workload('workload')
        mapping = Mapping('mapping', workload)
        ip = sys_platform.get_ip('ip')
        mapping.map_task(task1, ip)
        mapping.map_task(task2, ip)
        mapping.map_task(task3, ip)
        mapping.map_task(task4, ip)
        mapping.map_task(task5, ip)

        workload.add_tasks([start, task1, task2, task3, task4, task5, end])
        workload.connect_tasks('1', start, task1)
        workload.connect_tasks('2', start, task2)
        workload.connect_tasks('3', task2, task3)
        workload.connect_tasks('4', start, task4)
        workload.connect_tasks('5', start, task5)
        workload.connect_tasks('6', task3, end)
        workload.connect_tasks('7', task1, end)
        workload.connect_tasks('8', task4, end)
        workload.connect_tasks('9', task5, end)

        # adm_clk.period = 0.001
        # ddr_clk.period = 0.001

        speedsim = SpeedSim(sys_platform, workload, mapping)
        speedsim.set_platform_scheduler(BlockingScheduler)
        speedsim.add_extension('MTLNearFarFabric', MTLNearFarFabricMemDistribution)

        res = speedsim.simulate(10000)

        expected = pandas.DataFrame(data=[
            (0, 156.25, 'task1', 'ip/d', 0, 156.25),
            (0, 5000, 'task2', 'ip/exec_u', 0, 5000),
            (5000, 5039.06250, 'task3', 'ip/d', 0, 39.06250),
            (5039.06250, 5058.59375, 'task4', 'ip/d', 0, 19.53125),
            (5058.59375, 5105.46875, 'task5', 'ip/d', 0, 46.875)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected, check_dtype=False)
