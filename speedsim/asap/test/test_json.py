import tempfile
import unittest

from asap.buses import Bus
from asap.hw import Clock
from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.memories import Memory
from asap.states import (ActiveState, Condition, Expression, HierarchyState,
                         PowerState)
from asap.system_platform import Platform
from asap.utils import load_platform


class TestJson(unittest.TestCase):
    def test_simple_json(self):
        """
        Tests the json import and export - simple platform
            - 1 Clock, 1 IP, 1 Bus, 1 Memory
        """
        # Platform
        sys_platform = Platform("platform")

        # Clocks
        clk = Clock("clk", 0.01)
        sys_platform.add_clock(clk)

        # Ip
        p = Port('p')
        d = Driver('d', clk)
        exec_u = ExecutingUnit('exec_u', clk)
        ip = IP('ip', clk, [exec_u], [d], [p])
        ip.connect_driver(d, p)
        sys_platform.add_ip(ip)

        # Memory
        mem = Memory('memory', clk, 1024)
        sys_platform.add_memory(mem)

        # Buses
        bus1 = Bus('bus1', clk, 64)
        sys_platform.add_bus(bus1)

        sys_platform.connect_to_bus(p, bus1)
        sys_platform.connect_to_memory(bus1, mem)

        tmp_path = tempfile.NamedTemporaryFile('w', suffix='.json')
        tmp_path_name = tmp_path.name
        tmp_path.close()
        sys_platform.save(tmp_path_name)

        json_sys = load_platform(tmp_path_name)

        self.assertNotEqual(json_sys.get_ip('ip'), None)
        self.assertEqual(len(json_sys.get_ip('ip').executing_units), 1)
        self.assertNotEqual(json_sys.get_bus('bus1'), None)
        self.assertNotEqual(json_sys.get_memory('memory'), None)
        self.assertNotEqual(json_sys.get_clock('clk'), None)
        self.assertEqual(json_sys.get_clock('clk').period, 0.01)

    def test_complicated_json(self):
        """
        Tests the json import and export - complicated platform
            - 1 Clock,  2 Ips (4 Drivers, 2 executing unit, 3 Ports), 2 Buses, 1 Memory
        """
        # Platform

        sys_platform = Platform("platform")

        # Clocks
        clk = Clock('clk', 0.01)
        sys_platform.add_clock(clk)

        # Ip
        p1 = Port('p1')
        d1 = Driver('d1', clk)
        exec_u1 = ExecutingUnit('exec_u1', clk)
        ip1 = IP('ip1', clk, [exec_u1], [d1], [p1])
        ip1.connect_driver(d1, p1)
        sys_platform.add_ip(ip1)

        p2 = Port('p2')
        p3 = Port('p3')
        d2 = Driver('d2', clk, power_states=[PowerState('C0'), PowerState('C2')],
                    active_state=ActiveState('TestActive'))
        d3 = Driver('d3', clk, power_states=[PowerState('C0')])
        d4 = Driver('d4', clk)
        exec_u2 = ExecutingUnit('exec_u2', clk)
        ip2 = IP('ip2', clk, [exec_u2], [d2, d3, d4], [p2, p3])
        ip2.connect_driver(d2, p2)
        ip2.connect_driver(d3, p2)
        ip2.connect_driver(d4, p3)
        sys_platform.add_ip(ip2)

        # Memory
        mem = Memory('memory', clk, 1024)
        sys_platform.add_memory(mem)

        # Buses
        bus1 = Bus('bus1', clk, 64)
        bus2 = Bus('bus2', clk, 64)
        sys_platform.add_bus(bus1)
        sys_platform.add_bus(bus2)

        sys_platform.connect_to_bus(p1, bus1)
        sys_platform.connect_to_bus(p2, bus1)
        sys_platform.connect_to_bus(p3, bus2)
        sys_platform.connect_to_bus(bus1, bus2)
        sys_platform.connect_to_memory(bus2, mem)

        # States and expressions
        d2_sleep = Condition(d2, '<=', 'C0')
        d3_sleep = Condition(d2, '<=', 'C0')
        system_sleep_exp = Expression('DriversSleep', [d2_sleep, d3_sleep])
        system_sleep_state = HierarchyState('SystemSleep', 2, system_sleep_exp)
        sys_platform.system_states = [system_sleep_state]

        ip_sleep_state = HierarchyState('IpSleep', 2, system_sleep_exp)
        ip2.ip_states = [ip_sleep_state]

        tmp_path = tempfile.NamedTemporaryFile('w', suffix='.json')
        tmp_path_name = tmp_path.name
        tmp_path.close()
        sys_platform.save(tmp_path_name)
        json_sys = load_platform(tmp_path_name)

        # sys_platform.upload()
        # json_sys = Platform.download('test')

        self.assertNotEqual(json_sys.get_ip('ip1'), None)
        self.assertNotEqual(json_sys.get_ip('ip2'), None)
        self.assertEqual(len(json_sys.get_ip('ip2').drivers), 3)
        self.assertEqual(len(json_sys.get_ip('ip2').ports), 2)
        self.assertNotEqual(json_sys.get_bus('bus1'), None)
        self.assertNotEqual(json_sys.get_ip('ip2').get_driver('d2').get_power_state('C0'), None)
        self.assertEqual(json_sys.get_ip('ip2').get_driver('d2').active_state.name, 'TestActive')
        self.assertEqual(json_sys.get_bus('bus1').bus_width, 64)
        self.assertNotEqual(json_sys.get_bus('bus2'), None)
        self.assertNotEqual(json_sys.get_memory('memory'), None)
        self.assertEqual(json_sys.get_memory('memory').size, 1024)
        self.assertEqual(json_sys.system_states[0].name, 'SystemSleep')
        self.assertEqual(json_sys.system_states[0].idle_time, 2)
        self.assertEqual(json_sys.get_all_expressions()[0].name, 'DriversSleep')
