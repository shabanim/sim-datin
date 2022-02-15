import os
import unittest

from asap.utils import load_platform
from models.fabric.multi_memory import MultiMemoryExtension
from models.preemptions.preemptions import (RoundRobinExtension,
                                            RoundRobinScheduler)
from speedsim import SpeedSim


class TestRoundRobin(unittest.TestCase):
    def test_round_robin(self):
        """
        Tests the round robin extension with a simple workload
        """
        # simple platform for the test
        # Platform
        tests = os.path.dirname(__file__)
        file = os.path.join(tests, 'input/complex_platform.json')
        sys_platform = load_platform(file)

        ip1 = sys_platform.get_ip('ip1')
        ip1.get_driver('d1').attach_attribute(RoundRobinExtension.TIME_SLICE, 10)
        ip1.get_executing_unit('exec_u1').attach_attribute(RoundRobinExtension.TIME_SLICE, 10)
        ip2 = sys_platform.get_ip('ip2')
        # workloads
        from asap.workload import Task, Workload, TYPES
        from asap.mapping import Mapping

        # Workload
        start = Task('start', TYPES.START)
        end = Task('end', TYPES.END)
        task1 = Task('task1', type=TYPES.WRITE, write_bytes=70400)
        task1.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task2 = Task('task2', type=TYPES.WRITE, write_bytes=128000)
        task2.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task3 = Task('task3', type=TYPES.WRITE, write_bytes=70400)
        task3.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task4 = Task('task4', type=TYPES.READ, read_bytes=12500)
        task4.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        task5 = Task('task5', type=TYPES.PROC, processing_cycles=1500)
        task5.attach_attribute('MEMORY_TARGETS', {'memory': 100})

        workload = Workload('workload')
        mapping = Mapping('mapping', workload)
        workload.add_tasks([start, task1, task2, task3, task4, task5, end])
        workload.connect_tasks('1', start, task1)
        workload.connect_tasks('2', start, task2)
        workload.connect_tasks('3', start, task3)
        workload.connect_tasks('4', start, task5)
        workload.connect_tasks('5', task2, end)
        workload.connect_tasks('6', task3, end)
        workload.connect_tasks('7', task1, end)
        workload.connect_tasks('8', task4, end)
        workload.connect_tasks('9', task5, task4)

        mapping.map_task(task1, ip1)
        mapping.map_task(task2, ip2)
        mapping.map_task(task3, ip1)
        mapping.map_task(task4, ip1)
        mapping.map_task(task5, ip1)

        sim = SpeedSim(sys_platform, workload, mapping)
        sim.set_platform_scheduler(RoundRobinScheduler)
        sim.add_extension('MultiMemory', MultiMemoryExtension)
        sim.add_extension('RoundRobin', RoundRobinExtension)

        res = sim.simulate(1000)

        self.assertEqual(res[res['TRANSITION'] == 'task4']['DURATION'].sum(), 3.90625)
        self.assertEqual(res[res['TRANSITION'] == 'task1']['DURATION'].sum(), 21)
        self.assertEqual(res[res['TRANSITION'] == 'task3']['DURATION'].sum(), 19.046875)
