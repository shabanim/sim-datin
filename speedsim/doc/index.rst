.. reports documentation master file, created by
   sphinx-quickstart on Tue Jun 18 10:09:42 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Introduction
============
SPEEDSIM is an abstract system simulation application for architectural exploration.
It provides both command-line tool as well as Python API to simulate an abstract workload on a given hardware definition.

Example:

.. code-block:: python

   # Example of quick builds
   # Platform
   from asap.system_platform import Platform
   from asap.hw import Clock
   from asap.ips import IP, Driver, ExecutingUnit, Port
   from asap.buses import Bus
   from asap.memories import Memory
   s_clk = Clock(name='s_clk', period=0.005)
   g_clk = Clock(name='s_clk', period=0.01)
   a_clk = Clock(name='a_clk', period=0.001)
   sys_platform = Platform("Plat",
                        clocks=[a_clk, g_clk, s_clk],
                        ips=[IP('CPU', a_clk, executing_units=[ExecutingUnit('ex_u', a_clk)],
                             drivers=[Driver('dr', a_clk)], ports=[Port('p')], connections=[('dr', 'p')]),
                             IP('GT', g_clk, executing_units=[ExecutingUnit('ex_ug', g_clk)],
                             drivers=[Driver('dr_g', g_clk)], ports=[Port('p_g')], connections=[('dr_g', 'p_g')])],
                        buses=[Bus(name='bus1', clock=s_clk, bus_width=32), Bus(name='bus2', clock=s_clk),
                               Bus(name='bus3', clock=s_clk)],
                        memories=[Memory(name='mem', clock=s_clk, size=1024)],
                        ips_connections=[(('CPU', 'p'), 'bus1'), (('GT', 'p_g'), 'bus2')],
                        buses_connections=[('bus1', 'bus3'), ('bus2', 'bus3')],
                        memories_connections=[('bus3', 'mem')])

   # Workload
   from asap.workload import Workload, Task, Connection, TYPES
   start = Task('start', TYPES.START)
   t1 = Task('T1', processing_cycles=10)
   t2 = Task('T2', read_bytes=2048, processing_cycles=30, write_bytes=1024)
   end = Task('end', type=TYPES.END)

   wl = Workload('wl', tasks=[start, t1, t2, end],
                  connections=[Connection('con1', start, t1), Connection('con2', t1, t2), Connection('con3', t2, end)])

   # Mapping
   from asap.mapping import Mapping
   m = Mapping('m', wl)
   m.map_task(t1, sys_platform.get_ip('CPU'))
   m.map_task(t2, sys_platform.get_ip('GT'))

   # Sim
   from speedsim import SpeedSim
   sim = SpeedSim(sys_platform, wl, m)
   sim.simulate()

   # Example of building HW step by step
   from system_platform import Platform
   from hw import Clock, GlobalClock
   from ips import IP, Driver, ExecutingUnit, Port
   from buses import Bus
   from memories import Memory

   # Platform
   sys_platform = Platform("MTL")

   # Clocks
   clk = GlobalClock("global_clk", 0.01).instance
   a_clk = Clock("a_clk", 0.01)    # 10 ns
   sys_platform.add_clock(clk)

   # IP
   ip_p = Port('port')
   ip_dr = Driver('driver', a_clk)
   ip_ex = ExecutingUnit('ex_u', a_clk)

   ip = IP("IP", a_clk, [ip_ex], [ip_dr], [ip_p])
   ip.connect_driver(ip_dr, ip_p)
   sys_platform.add_ip(ip)

   # Bus
   bus = Bus('bus', clk, 64)
   sys_platform.add_bus(bus)

   # Memory
   ddr = Memory('DDR', clk, 1024)
   sys_platform.add_memory(ddr)

   # Connectivity
   sys_platform.connect_to_memory(bus, ddr)
   sys_platform.connect_to_bus(ip_p, bus)

   # Validation
   sys_platform.validate_platform()


   # Example of building workload
   from workload import Workload, Task, Connection

   wl = Workload('abstract')
   start = Task('start', TYPES.START)
   wl.add_task(start)
   t1 = Task('task1', TYPES.PROC)
   wl.add_task(t1)
   t.attach_attribute(MappingDesc.MEMORY_TARGET, 'DDR')
   wl.connect_tasks('con1', start, t1)

   end = Task('end', type=TYPES.END)
   wl.add_task(end)
   wl.connect_tasks('con2', t1, end)

   # Example of mapping
   from mapping import Mapping
   m = Mapping('mapping')
   m.map_task(t1, ip)

   # Running simulation
   from speedsim import SpeedSim
   speedsim = SpeedSim(sys_platform, wl, m)
   res = speedsim.simulate(50000)

Platform Classes
================
.. autosummary::
   asap.system_platform.Platform
   asap.buses.Bus
   asap.memories.Memory
   asap.ips.ExecutingUnit
   asap.ips.Driver
   asap.ips.Port
   asap.ips.IP
   asap.states.PowerState
   asap.states.ActiveState
   asap.states.Condition
   asap.states.Expression
   asap.states.HierarchyState

Workload Classes
================
.. autosummary::
   asap.workload.Task
   asap.workload.WlTask
   asap.workload.Connection
   asap.workload.Workload
   asap.mapping.Mapping

Schedulers
==========
.. autosummary::
   asap.schedulers.BaseSystemScheduler
   asap.schedulers.SystemScheduler
   asap.schedulers.BlockingScheduler
   asap.schedulers.RPWScheduler

Simulation
==========
.. autosummary::
   pnets.simulation.EVENTS
   speedsim.SpeedSim

Functions
=========
.. autosummary::
   asap.utils.load_platform
   asap.utils.from_pnml_model
   speedsim.SpeedSim.simulate

Post processing Functions
=========================
.. autosummary::
   post_processing.utils.get_hw_runtime_table
   post_processing.utils.get_hw_analysis
   post_processing.utils.hw_analysis_to_excel
   post_processing.utils.task_analysis_to_excel
   post_processing.utils.analysis_to_excel
   post_processing.utils.analysis_to_html
   post_processing.utils.analysis_to_html
   post_processing.utils.create_analysis_comparison
   post_processing.tables.get_concurrency_table
   post_processing.tables.show_interactive_table
   post_processing.graphs.create_task_analysis_fig
   post_processing.graphs.create_states_figs
   post_processing.graphs.create_step_figs
   post_processing.graphs.create_resource_fig

Module: Hardware
================
.. automodule:: asap.system_platform
    :members:
    :no-undoc-members:

.. automodule:: asap.buses
    :members:
    :no-undoc-members:

.. automodule:: asap.memories
    :members:
    :no-undoc-members:

.. automodule:: asap.ips
    :members:
    :no-undoc-members:

.. automodule:: asap.states
    :members:
    :no-undoc-members:

Module: Workload
================
.. automodule:: asap.workload
    :members:
    :no-undoc-members:

.. automodule:: asap.mapping
    :members:
    :no-undoc-members:

.. automodule:: asap.counters
    :members:
    :no-undoc-members:

Module: Schedulers
==================
.. automodule:: asap.schedulers
    :members:
    :no-undoc-members:

Module: Extensions
==================
.. automodule:: asap.extensions
    :members:
    :no-undoc-members:

Module: Utils
=============
.. automodule:: asap.utils
    :members:
    :no-undoc-members:

Module: SpeedSim
================
.. automodule:: speedsim
    :members:
    :no-undoc-members:

Module: Post Processing
=======================
.. automodule:: post_processing.graphs
    :members:
    :no-undoc-members:

.. automodule:: post_processing.tables
    :members:
    :no-undoc-members:

.. automodule:: post_processing.utils
    :members:
    :no-undoc-members:

Module: pnets
=============
.. automodule:: pnets
    :members:
    :no-undoc-members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`