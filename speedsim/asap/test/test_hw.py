import unittest

from asap.buses import Bus
from asap.hw import Clock
from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.memories import Memory
from asap.system_platform import Platform


class TestHw(unittest.TestCase):
    def test_buses(self):
        """
        Tests the bus add and connect option:
            - Creates simple platform
            - Creates multiple buses
            - Validate correct connectivity and existence
            - Validate incorrect connectivity
        """
        # Platform
        sys_platform = Platform("platform")

        # Clocks
        clk = Clock("global_clk", 0.01)
        sys_platform.add_clock(clk)

        # Ip
        p = Port('p')
        d = Driver('d', clk)
        exec_u = ExecutingUnit('exec_u', clk)
        ip = IP('ip', clk, [exec_u], [d], [p])
        ip.connect_driver(d, p)
        sys_platform.add_ip(ip)

        # Memory
        m = Memory('memory', clk, 1024)
        sys_platform.add_memory(m)

        # Buses
        for i in range(1, 11):
            sys_platform.add_bus(Bus('bus'+str(i), clk, 64))

        sys_platform.connect_to_bus(sys_platform.get_bus('bus1'), sys_platform.get_bus('bus2'))
        sys_platform.connect_to_bus(sys_platform.get_bus('bus1'), sys_platform.get_bus('bus3'))
        for i in range(4, 8):
            sys_platform.connect_to_bus(sys_platform.get_bus('bus2'), sys_platform.get_bus('bus'+str(i)))
        for i in range(8, 11):
            sys_platform.connect_to_bus(sys_platform.get_bus('bus3'), sys_platform.get_bus('bus'+str(i)))
        sys_platform.connect_to_bus(p, sys_platform.get_bus('bus1'))
        for i in range(4, 10):
            sys_platform.connect_to_bus(sys_platform.get_bus('bus'+str(i)), sys_platform.get_bus('bus10'))
        sys_platform.connect_to_memory(sys_platform.get_bus('bus10'), m)

        try:
            sys_platform.validate_platform()
        except ValueError:
            self.assertFalse(True)

        for i in range(1, 11):
            self.assertNotEqual(sys_platform.get_bus('bus'+str(i)), None)
        self.assertEqual(sys_platform.get_bus('bus11'), None)

        bus_fail = Bus('bus_fail', clk, 64)
        sys_platform.add_bus(bus_fail)

        self.assertRaises(ValueError, sys_platform.validate_platform)

    def test_ips(self):
        """
        Tests the ips add and connect option
            - Creates simple platform
            - Creates multiple ips
            - Validate correct connectivity and existence
            - Validate incorrect connectivity (free port)
        """
        # Platform
        sys_platform = Platform("platform")

        # Clocks
        clk = Clock("global_clk", 0.01)
        sys_platform.add_clock(clk)

        # Ip
        p1 = Port('p1')
        p2 = Port('p2')
        d1 = Driver('d1', clk)
        d2 = Driver('d2', clk)
        d3 = Driver('d3', clk)
        exec_u1 = ExecutingUnit('exec_u1', clk)
        exec_u2 = ExecutingUnit('exec_u2', clk)
        exec_u3 = ExecutingUnit('exec_u3', clk)
        exec_u4 = ExecutingUnit('exec_u4', clk)
        ip1 = IP('ip1', clk, [exec_u1, exec_u2, exec_u3, exec_u4], [d1, d2, d3], [p1, p2])
        ip1.connect_driver(d1, p1)
        ip1.connect_driver(d2, p1)
        ip1.connect_driver(d3, p2)
        sys_platform.add_ip(ip1)

        p = Port('p')
        d = Driver('d', clk)
        exec_u = ExecutingUnit('exec_u', clk)
        ip2 = IP('ip2', clk, [exec_u], [d], [p])
        ip2.connect_driver(d, p)
        sys_platform.add_ip(ip2)

        ip3_p = Port('ip3_p')
        ip3_d = Driver('ip3_d', clk)
        exec_uu = ExecutingUnit('exec_uu', clk)
        ip3 = IP('ip3', clk, [exec_uu], [ip3_d], [ip3_p])
        ip3.connect_driver(ip3_d, ip3_p)
        sys_platform.add_ip(ip3)

        # Memory
        m = Memory('memory', clk, 1024)
        sys_platform.add_memory(m)

        # Buses
        bus1 = Bus('bus1', clk, 64)
        sys_platform.add_bus(bus1)

        sys_platform.connect_to_bus(p1, bus1)
        sys_platform.connect_to_bus(p2, bus1)
        sys_platform.connect_to_bus(p, bus1)
        sys_platform.connect_to_bus(ip3_p, bus1)
        sys_platform.connect_to_memory(bus1, m)

        try:
            sys_platform.validate_platform()
        except ValueError:
            self.assertFalse(True)

        for i in range(1, 3):
            self.assertNotEqual(sys_platform.get_ip('ip'+str(i)), None)
        self.assertEqual(sys_platform.get_bus('ip4'), None)

        ip1.add_port(Port('empty_port'))

        self.assertRaises(ValueError, sys_platform.validate_platform)

    def test_memory(self):
        """
        Tests the memory add and connect option
            - Creates simple platform
            - Creates multiple memories
            - Validate correct connectivity and existence
            - Validate incorrect connectivity
        """
        # Platform
        sys_platform = Platform("platform")

        # Clocks
        clk = Clock("global_clk", 0.01)
        sys_platform.add_clock(clk)

        # Ip
        p = Port('p')
        d = Driver('d', clk)
        exec_u = ExecutingUnit('exec_u', clk)
        ip = IP('ip', clk, [exec_u], [d], [p])
        ip.connect_driver(d, p)
        sys_platform.add_ip(ip)

        # Buses
        bus1 = Bus('bus1', clk, 64)
        sys_platform.add_bus(bus1)

        # Memory
        for i in range(1, 9):
            m = Memory('m'+str(i), clk, 1024)
            sys_platform.add_memory(m)
            sys_platform.connect_to_memory(bus1, m)

        sys_platform.connect_to_bus(p, bus1)

        try:
            sys_platform.validate_platform()
        except ValueError:
            self.assertFalse(True)

        for i in range(1, 9):
            self.assertNotEqual(sys_platform.get_memory('m' + str(i)), None)
        self.assertEqual(sys_platform.get_bus('m9'), None)

        mem_fail = Memory('mem_fail', clk, 1024)
        sys_platform.add_memory(mem_fail)

        self.assertRaises(ValueError, sys_platform.validate_platform)
