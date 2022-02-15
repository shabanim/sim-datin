#!/p/dpg/arch/perfhome/python/miniconda3/bin/python3 -u
# Platform modules
from asap.system_platform import Platform
from asap.hw import Clock, GlobalClock
from asap.ips import IP, Driver, ExecutingUnit, Port
from asap.buses import Bus
from asap.memories import Memory
from asap.strings import PENALTY

PENALTY_VAL = 1

# Platform
sys_platform = Platform("MTL")

# Clocks
clk = GlobalClock("global_clk", 0.01).instance
a_clk = Clock("a_clk", 0.01)  # 10 ns
b_clk = Clock("b_clk", 0.01)  # 10 ns
g_clk = Clock("g_clk", 0.01)  # 10 ns
sys_platform.add_clock(clk)
sys_platform.add_clock(a_clk)
sys_platform.add_clock(b_clk)
sys_platform.add_clock(g_clk)

# IPs:
# - Ports
# - Drivers
# - Executing units

# Atoms
atoms = dict()
for atom_name in ["CPU"]:
    p = Port(atom_name + "_p")
    dr = Driver("driver", a_clk)
    ex_units = list()
    for ex in ["cpu{}".format(j) for j in range(8)]:
        ex_units.append(ExecutingUnit(ex, a_clk))
    atom = IP(atom_name, a_clk, ex_units, [dr], [p])
    atom.connect_driver(dr, p)
    atom.attach_attribute(PENALTY, PENALTY_VAL)
    sys_platform.add_ip(atom)
    atoms[atom_name] = (atom, p)

# GT
gt_p = Port('p')
gt_dr = Driver('VC0', g_clk)
gt_ex = ExecutingUnit('cpu0', g_clk)

gt = IP("GEN", g_clk, [gt_ex], [gt_dr], [gt_p])
gt.connect_driver(gt_dr, gt_p)
sys_platform.add_ip(gt)

# IP Buses
quad1_bus = Bus('quad1_bus', a_clk, 64)
sys_platform.add_bus(quad1_bus)

# System buses
bus1 = Bus('bus1', b_clk, 64)
bus2 = Bus('bus2', clk, 64)
sys_platform.add_bus(bus1)
sys_platform.add_bus(bus2)

# Memories
llc = Memory('LLC', a_clk, 1024)
ddr = Memory('DDR', clk, 1024)
sys_platform.add_memory(llc)
sys_platform.add_memory(ddr)

# Connecting
sys_platform.connect_to_bus(atoms["CPU"][1], quad1_bus)

sys_platform.connect_to_bus(quad1_bus, bus1)
sys_platform.connect_to_bus(bus1, bus2)

sys_platform.connect_to_memory(bus1, llc)
sys_platform.connect_to_memory(bus2, ddr)
sys_platform.connect_to_bus(gt_p, bus2)

sys_platform.validate_platform()

sys_platform.dump_power_connectivity_file('/nfs/iil/proj/dt/vppnp01/work/saeedess/speedsim_2/speedsim/models/power/apm')


from asap.schedulers import BaseSystemScheduler
from asap.mapping import MappingEntity
from asap.strings import SchedulingState


class AtomFirstScheduler:
    """
    Atom first scheduler:
        prefer tasks that should be mapped to resource of type core to atoms first with penalty, if all atoms are busy then map to CPU
    """
    def __init__(self, system_mgr):
        self._system_mgr = system_mgr
        self._base_scheduler = BaseSystemScheduler(self._system_mgr)
        self._atoms = self._get_ips(['CPU'])
        self._gt = self._get_ips(['GEN'])[0]

    def _get_ips(self, names):
        ips = list()
        for ip in self._system_mgr.sys_platform.ips:
            if ip.name in names:
                ips.append(ip)
        return ips

    def schedule_task(self, task, resource=None):
        if resource is not None:
            return self._base_scheduler.schedule_task(task, [MappingEntity(task, resource)])
        task_map_type = task.get_attribute('MAP_TYPE', None)
        if task_map_type is None:
            return self._base_scheduler.schedule_task(task, list())
        elif task_map_type == 'GT':
            return self._base_scheduler.schedule_task(task, [MappingEntity(task, self._gt)])
        elif task_map_type == 'Core':
            r, t = self._base_scheduler.schedule_task(task, [MappingEntity(task, a) for a in self._atoms])
            return r, t
        else:
            return self._base_scheduler.schedule_task(task, list())

    def on_task_finish(self, task):
        self._base_scheduler.on_task_finish(task)


from pnets.pn_model import PnmlModel
fd = open('/nfs/iil/proj/dt/vppnp01/work/saeedess/my_ws/SpeedSim/tg/vpb_9.178_9.3118.extended.pnml', 'r')
vpb_pnml_model = PnmlModel.read(fd)
"""
Simple test with the following PN model:
              (start)
                 |
            [cpu_task1]
              //   \\
            (1)    (1)
            //       \\
      [gpu_task1]  [cpu_task2]
           \\         //
           (1)      (1)
             \\     //
             [cpu_task3]
                 |
               (end)
"""
transitions = [
    PnmlModel.Transition("cpu_task1", id="cpu_task1", cycles=100, runtime=100, hw_resource="CPU"),
    PnmlModel.Transition("gpu_task1", id="gpu_task1", cycles=200, runtime=200, hw_resource="GT_GFX"),
    PnmlModel.Transition("cpu_task2", id="cpu_task2", cycles=220, runtime=220, hw_resource="CPU"),
    PnmlModel.Transition("cpu_task3", id="cpu_task3", cycles=150, runtime=150, hw_resource="CPU")
]
places = [
    PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
    PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->gpu_task1", init=0, buff_size=1),
    PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->cpu_task2", init=0, buff_size=1),
    PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="gpu_task1->cpu_task3", init=0, buff_size=1),
    PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task2->cpu_task3", init=0, buff_size=1),
    PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end")
]
arcs = [
    PnmlModel.Arc("start", "cpu_task1", "", weight=1),

    PnmlModel.Arc("cpu_task1", "cpu_task1->gpu_task1", "", weight=1),
    PnmlModel.Arc("cpu_task1->gpu_task1", "gpu_task1", "", weight=1),

    PnmlModel.Arc("cpu_task1", "cpu_task1->cpu_task2", "", weight=1),
    PnmlModel.Arc("cpu_task1->cpu_task2", "cpu_task2", "", weight=1),

    PnmlModel.Arc("gpu_task1", "gpu_task1->cpu_task3", "", weight=1),
    PnmlModel.Arc("gpu_task1->cpu_task3", "cpu_task3", "", weight=1),

    PnmlModel.Arc("cpu_task2", "cpu_task2->cpu_task3", "", weight=1),
    PnmlModel.Arc("cpu_task2->cpu_task3", "cpu_task3", "", weight=1),

    PnmlModel.Arc("cpu_task3", "end", "", weight=1),
]

net = PnmlModel.Net(places=places, transitions=transitions, arcs=arcs)
model = PnmlModel(nets=[net])

from asap.strings import TaskMetaData
from asap.utils import from_pnml_model, create_rpw_task
from speedsim import SpeedSim
from models.power.apm.apm import APM, SpeedSimListener
from models.power.apm.updater import Updater
from asap.workload import TYPES



# hw_resources = {'CPU': {'resource': atoms['AtomQuad0'][0], 'attributes': {'MAP_TYPE': 'Core'}}, 'GT_GFX': {'resource': gt, 'attributes': {'MAP_TYPE': 'GT'}}}
# workload, mapping = from_pnml_model(vpb_pnml_model, 'workload', {}, hw_resources)
# for s in workload.get_start_tasks():
#     s.set_property(TaskMetaData.ITERATIONS, 10)


a_clk.period = 0.001 # 2000MHz
b_clk.period = 0.001
g_clk.period = 0.001 #


hw_resources = {'CPU': {'resource': atoms['CPU'][0], 'attributes': {'MAP_TYPE': 'Core'}}, 'GT_GFX': {'resource': gt, 'attributes': {'MAP_TYPE': 'GT'}}}
reference_frequency={'CPU': 1000, 'GT_GFX': 800}
# tasks_att = {'hw_resource': {'values': ['CPU', 'GT_GFX'], 'flunction': create_rpw_task, 'split': 1}}
workload, mapping = from_pnml_model(model, 'workload', reference_frequency, hw_resources)

sys_platform.reset()

speedsim = SpeedSim(sys_platform, workload, mapping, sim_scheduler=APM, system_scheduler=AtomFirstScheduler)
listener = SpeedSimListener()
updater = Updater(listener, apm=speedsim.sim_scheduler)
# speedsim.sim_scheduler.instantiate(updater, listener, 1.0, "power_file_system_states.csv", "connectivity_base_platform_power.csv")
speedsim.sim_scheduler.instantiate(updater, listener, 1.0, "MTL_power_states.csv", "MTL_connectivity.csv")
res = speedsim.simulate(1000000)
res.to_csv('/nfs/iil/proj/dt/vppnp01/work/saeedess/my_ws/SpeedSim/res_apm_w_pmu.csv')
cstates = speedsim.sim_scheduler.get_cstates_data()
cstates.to_csv('/nfs/iil/proj/dt/vppnp01/work/saeedess/my_ws/SpeedSim/stats_apm_w_pmu.csv')