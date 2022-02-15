import json
import sys
import os
import pandas

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

paths = [os.path.join(PROJECT_DIR, 'speedsim'),
         os.path.join(PROJECT_DIR, 'micro_service', 'analysis'),
         os.path.join(PROJECT_DIR, 'micro_service')]
sys.path.extend(paths)

from .overlap_analysis import _get_source, _get_target, GPUs, EX_UNITS_PER_GPU

from report_objects import OverlapSummaryReport
from asap.workload import Workload, Task, TYPES, Connection
from asap.ips import IP, ExecutingUnit, Driver, Port
from asap.hw import Clock
from asap.buses import Bus
from asap.memories import Memory
from asap.system_platform import Platform
from asap.schedulers import SystemScheduler
from asap.mapping import MappingEntity
from speedsim import SpeedSim
from post_processing.utils import AnalysisData
from .graph_transformation import twox_fwd_pass


class PVC_TASK_TYPE:
    COMM_SO = "COMM_SO"
    COMM_SU = "COMM_SU"
    CPU = "CPU"
    NVME = "NVME"
    GPU = "GPU"
    RMEM = "RMEM"

counter = 0

# Scheduler
class ZeroInfScheduler(SystemScheduler):
    def __init__(self, system_mgr, properties=None, platform_scheduler=None):
        super().__init__(system_mgr, properties, platform_scheduler)
        self._gpus = self._get_ips(['GPU_{}'.format(gpu) for gpu in range(GPUs)])
        self._gpus_drivers = self._get_drivers(self._gpus)
        self._cpus = self._get_ips(['CPU'])
        self._cpus_drivers = self._get_drivers(self._cpus)
        print("total drivers:",len(self._cpus_drivers))

    def _get_drivers(self, ips):
        drs = []
        for ip in ips:
            for dr in ip.drivers:
                drs.append(dr)
        return drs

    def _get_ips(self, names):
        ips = list()
        for ip in self._system_mgr.sys_platform.ips:
            if ip.name in names:
                ips.append(ip)
        return ips

    def schedule_task(self, task, resource=None):
        if resource is not None:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, resource)])
        task_type = task.get_attribute('TASK_TYPE')
        #print(task_type)
        # debug print("task name: {}, task type: {}".format(task.name, task_type))
        if task_type == PVC_TASK_TYPE.CPU:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._cpus[0])])
        if task_type == PVC_TASK_TYPE.GPU:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._gpus[0])])
        if task_type == PVC_TASK_TYPE.COMM_SO or task_type == PVC_TASK_TYPE.COMM_SU:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._gpus_drivers[0])])
        if task_type == PVC_TASK_TYPE.NVME:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._cpus_drivers[0])])
        if task_type == PVC_TASK_TYPE.RMEM:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._cpus_drivers[1])])

    def on_task_finish(self, task):
        self._platform_scheduler.on_task_finish(task)


def get_platform(knobs, ref_period):
    # HW
    platform = Platform('PVC')
    clk = Clock('GPU_clk', ref_period)
    bus_clk = Clock('BUS_clk', ref_period)
    mem_clk = Clock('MEM_clk', ref_period)
    platform.add_clocks([clk, bus_clk, mem_clk])

    bus = Bus('Bus', bus_clk)
    platform.add_bus(bus)
    mem = Memory('Memory', mem_clk, 1024)

    platform.add_memory(mem)

    platform.connect_to_memory(bus, mem)

    if knobs['so_overlap_scaleup']:
        bus_so = Bus("Bus_so", bus_clk)
        platform.add_bus(bus_so)
        mem_so = Memory('Memory_so', mem_clk, 1024)
        platform.add_memory(mem_so)
        platform.connect_to_memory(bus_so, mem_so)

    for gpu in range(GPUs):
        drs = []
        ports = []
        for idx in range(0, 1):
            drs.append(Driver('GPU_{}_COMMS'.format(gpu, idx), clk))
            ports.append(Port('GPU_{}_P'.format(gpu)))

        if knobs['so_overlap_scaleup']:
            dr_so = Driver('GPU_{}_COMMS_SO'.format(gpu), clk)
            p_so = Port('GPU_{}_SO_P'.format(gpu))
            drs.append(dr_so)
            ports.append(p_so)

        ex_units = []
        for ex_u in range(EX_UNITS_PER_GPU):
            ex_units.append(ExecutingUnit('GPU_{}_COMP_{}'.format(gpu, ex_u), clk))
        gpu = IP('GPU_{}'.format(gpu), clk, ex_units, drs, ports)
        #     gpu.scheduler = GPU_IPScheduler()

        for idx, dr in enumerate(drs):
            gpu.connect_driver(dr, ports[idx])

        platform.add_ip(gpu)
        platform.connect_to_bus(ports[0], bus)
        if knobs['so_overlap_scaleup']:
            gpu.connect_driver(dr_so, p_so)
            platform.connect_to_bus(p_so, bus_so)

    nvme = Memory('NVME-Memory', mem_clk, 1024)
    platform.add_memory(nvme)
    cpu_eu = ExecutingUnit('CPU_COMP', clk)
    cpu_dr = Driver('CPU_NVME', clk)
    cpu_pt = Port('CPU_Port_1', clk)
    cpu_dr_1 = Driver('RMEM_CPU',clk)
    cpu_pt_1 = Port('CPU_port_2',clk)
    cpu = IP('CPU', clk, [cpu_eu], [cpu_dr,cpu_dr_1], [cpu_pt,cpu_pt_1])
    cpu.connect_driver(cpu_dr, cpu_pt)
    cpu.connect_driver(cpu_dr_1,cpu_pt_1)
    platform.add_ip(cpu)
    platform.connect_to_bus(cpu_pt, bus)
    platform.connect_to_memory(bus, nvme)
    remote_memory = Memory('remote-memory',mem_clk,1024)
    platform.add_memory(remote_memory)
    platform.connect_to_bus(cpu_pt_1, bus)
    platform.connect_to_memory(bus,remote_memory)

    platform.validate_platform()

    return platform


def get_task(node, sub_task, alias, pass2msg):
    layer_pass = node['data']['Layer']['l_pass']
    layer_name = node['data']['Layer']['Layer Name']
    processing_cycles = float(node['data']['Layer'][alias])
    msg_size = float(node['data']['Layer'][pass2msg[layer_pass]])
    if('f-ip' in sub_task):
        msg_size = float(node['data']['Layer']['data_remote_storage_msg_size'])
    if('f-w' in sub_task or 'o-w' in sub_task):
        msg_size = float(node['data']['Layer']['wt_remote_storage_msg_size'])
    if (('f-w-remote-cpu' in sub_task) or ('f-ip-remote-cpu' in sub_task) or ('f-w-cpu-nvme' in sub_task)) and '2_encoder_token_embedding' in layer_name:
        processing_cycles = 0
        msg_size = 0
    proc = Task(sub_task + '_' + layer_name, TYPES.PROC,
                processing_cycles=processing_cycles,
                layer_pass=layer_pass, msg_size=msg_size, sub_task=sub_task)

    proc.attach_attribute('SUB_TASK_TYPE', sub_task)
    if '-so' in sub_task:
        proc.attach_attribute('TASK_TYPE', PVC_TASK_TYPE.COMM_SO)
    elif '-su' in sub_task:
        proc.attach_attribute('TASK_TYPE', PVC_TASK_TYPE.COMM_SU)
    elif 'remote' in sub_task:
        proc.attach_attribute('TASK_TYPE',PVC_TASK_TYPE.RMEM)
    elif 'nvme' in sub_task:
        proc.attach_attribute('TASK_TYPE', PVC_TASK_TYPE.NVME)
    elif 'cpu' in sub_task:
        proc.attach_attribute('TASK_TYPE', PVC_TASK_TYPE.CPU)
    else:
        proc.attach_attribute('TASK_TYPE', PVC_TASK_TYPE.GPU)

    return proc, processing_cycles


def get_sub_tasks(node, sub_tasks, pass2msg, conn,knobs):
    tasks = []
    connections = []
    processing_cycles = 0
    for sub_task, alias in sub_tasks.items():
        task, cycles = get_task(node, sub_task, alias, pass2msg)
        tasks.append(task)
        processing_cycles += cycles
    for idx in range(0, len(tasks) - 1):
        src = tasks[idx]
        dst = tasks[idx + 1]
        if('f-w-cpu-nvme' in src.name):
            global counter 
            counter+=1
            connections.append(Connection(str(conn), src, dst, put_samples=knobs['num_iterations'], get_samples=1, buf_size=knobs['num_iterations']))
        else:
            connections.append(Connection(str(conn), src, dst))
        conn += 1
    return tasks, connections, conn, processing_cycles


def add_verbose_cols(res, workload):
    task2attributes = {}
    for task in workload.tasks:
        msg_size = task.get_attribute('msg_size')
        sub_task = task.get_attribute('sub_task')
        layer_pass = task.get_attribute('layer_pass')
        task_type = task.get_attribute('TASK_TYPE')
        task2attributes[task.name] = (layer_pass, task_type, sub_task, msg_size)

    _layer_pass = []
    _msg_size = []
    _task_type = []
    _sub_task = []
    for index, row in res.iterrows():
        trans = row['TRANSITION']
        layer_pass, task_type, sub_task, msg_size = task2attributes[trans]
        _layer_pass.append(layer_pass)
        _task_type.append(task_type)
        _sub_task.append(sub_task)
        _msg_size.append(msg_size)

    res['Pass'] = _layer_pass
    res['Msg Size (bytes)'] = _msg_size
    res['Task Type'] = _task_type
    res['Sub Task'] = _sub_task

    return res


def intervals_union(intervals_list):
    """
    Returns the union of the intervals in the intervals list

    Example: intervals_union([(1, 10), (10, 15), (11, 12), (14, 16), (17, 18)])
    Out: [(1, 16), (17, 18)]

    :param intervals_list: a list of the form (from, to)
    :return: returns a list of intervals of the form (from, to) the represents the union of the input
    """
    sorted_by_lower_bound = sorted(intervals_list, key=lambda tup: tup[0])
    merged = []

    for higher in sorted_by_lower_bound:
        if not merged:
            merged.append(higher)
        else:
            lower = merged[-1]
            # test for intersection between lower and higher:
            # we know via sorting that lower[0] <= higher[0]
            if higher[0] <= lower[1]:
                upper_bound = max(lower[1], higher[1])
                merged[-1] = (lower[0], upper_bound)  # replace by merged interval
            else:
                merged.append(higher)
    return merged


def get_intervals(df, filter_columns, operand="and"):
    import copy
    temp_df = copy.deepcopy(df)
    temp_df.columns = [column.replace(" ", "_") for column in temp_df.columns]

    query = ""
    if len(filter_columns) > 1:
        for idx, (col, val) in enumerate(filter_columns):
            if idx == len(filter_columns) - 1:
                query += "{}=='{}'".format(col.replace(' ', '_'), val, operand)
            else:
                query += "{}=='{}' {} ".format(col.replace(' ', '_'), val, operand)
    else:
        query = "".join("{}=='{}'".format(col.replace(' ', '_'), val) for col, val in filter_columns)

    res = temp_df.query(query, inplace=False)
    intervals = []
    for index, row in res.iterrows():
        start = row['START_(ms)']
        end = row['FINISH_(ms)']
        intervals.append((start, end))

    return intervals


def interval_sum(intervals):
    sum = 0
    for interval in intervals:
        sum += (interval[1] - interval[0])
    return sum


def get_overlap_stats(res):
    duration = res.groupby(['Task Type', 'Sub Task']).sum().to_dict()['DURATION (ms)']

    def get_subkey_sum(val_dict, subkey):
        # if subkey occurs in key of dict, then consider value for sum
        sum = 0
        for key in val_dict.keys():
            if subkey in list(key):
                sum += val_dict[key]
        return sum

    compute_time = get_subkey_sum(duration, 'GPU')
    cpu_time = get_subkey_sum(duration, 'CPU')
    nvme_time = get_subkey_sum(duration, 'NVME')
    scale_up_time = get_subkey_sum(duration, 'COMM_SU')
    scale_out_time = get_subkey_sum(duration, 'COMM_SO')
    scale_out_time_pod = sum([get_subkey_sum(duration, name) for name in ['f-allgather-so_pod','b-w-rs-so_pod','b-d-allgather-so_pod']])
    scale_out_time_nic = sum(
        [get_subkey_sum(duration, name) for name in ['f-allgather-so_nic', 'b-w-rs-so_nic', 'b-d-allgather-so_nic']])
    remote_time = get_subkey_sum(duration,'RMEM')

    sim_time = res['FINISH (ms)'].max()

    scale_up_overlap_time = sim_time - interval_sum(
        intervals_union(get_intervals(res,
                                      [('Task Type','GPU'),
                                       ('Task Type','COMM_SO'),
                                       ('Task Type', 'CPU'),
                                       ('Task Type', 'NVME'),
                                       ('Task Type','RMEM')],
                                      operand='or')))

    scale_out_overlap_time = sim_time - interval_sum(
        intervals_union(get_intervals(res,
                                      [('Task Type','GPU'),
                                       ('Task Type','COMM_SU'),
                                       ('Task Type', 'CPU'),
                                       ('Task Type', 'NVME'),
                                       ('Task Type','RMEM')],
                                      operand='or')))

    cpu_overlap_time = sim_time - interval_sum(
        intervals_union(get_intervals(res,
                                      [('Task Type','GPU'),
                                       ('Task Type','COMM_SO'),
                                       ('Task Type', 'COMM_SU'),
                                       ('Task Type', 'NVME'),
                                       ('Task Type','RMEM')],
                                      operand='or')))

    nvme_overlap_time = sim_time - interval_sum(
        intervals_union(get_intervals(res,
                                      [('Task Type','GPU'),
                                       ('Task Type','COMM_SO'),
                                       ('Task Type', 'CPU'),
                                       ('Task Type', 'COMM_SU'),
                                       ('Task Type','RMEM')],
                                      operand='or')))

    remote_overlap_time = sim_time - interval_sum(
        intervals_union(get_intervals(res,
                                      [('Task Type','GPU'),
                                       ('Task Type','COMM_SO'),
                                       ('Task Type', 'CPU'),
                                       ('Task Type', 'NVME'),
                                       ('Task Type', 'COMM_SU')],
                                      operand='or')))

    data = [["Compute time", compute_time, compute_time],
            ["Cpu time", cpu_time, cpu_overlap_time],
            ["Nvme time", nvme_time, nvme_overlap_time],
            ['Remote time',remote_time,remote_overlap_time],
            ["Scale up", scale_up_time, scale_up_overlap_time],
            ["Scale out", scale_out_time, scale_out_overlap_time],
            ["Scale out pod", scale_out_time_pod, 0],
            ["Scale out nic", scale_out_time_nic, 0],

            ]
    df = pandas.DataFrame(data, columns=['Metric', 'Nov-Overlap (ms)', 'Exposed (overlapped) (ms)'])

    return df

def get_sim_summary(res):
    data = [["Total time",res['DURATION (ms)'].sum() , res['FINISH (ms)'].max()]]
    return pandas.DataFrame(data, columns=['Metric', 'Nov-Overlap (ms)', 'Overlapped (ms)'])

def make_cyclic_connection(from_node,to_node,conn):
    connections = []
    connections.append(Connection(str(conn),from_node,to_node,init = 1))
    conn+=1
    return connections,conn

def speedsim_analysis_zero_inf(workload_json, knobs, include_timeline=False, network_name=None):
    # Loading workload as a dictionary from json file

    wl_json_fd = open(workload_json, 'r')
    wl_json = json.load(wl_json_fd)

    if knobs['fwd_2x']:
        wl_json = twox_fwd_pass(wl_json)

    successor_dict = {}
    predecessor_dict = {}

    for link in (wl_json["links"]):
        source = _get_source(link, wl_json)
        dst = _get_target(link, wl_json)
        if "bwd_" not in source:
            last_fwd_source = source
        if source not in successor_dict.keys():
            successor_dict[source] = []
        successor_dict[source].append(dst)
        if dst not in predecessor_dict.keys():
            predecessor_dict[dst] = []
        predecessor_dict[dst].append(source)

    start_layers = list(successor_dict.keys() - predecessor_dict.keys())

    ref_freq = knobs["frequency_in_Ghz"] * 1000  # 1.5GH = 1500Mhz = 0.000666us
    ref_period = 1 / ref_freq  # 1.5GH = 1500Mhz = 0.000666us

    pass2msg = {'fwd': 'wt_grad_msg_size',
                'oth': 'wt_grad_msg_size',
                'bwd-w': 'wt_grad_msg_size',
                'bwd-d': 'wt_grad_msg_size',
                'upd': 'wt_grad_msg_size'}

    fwd_sub_task = {'f-w-remote-cpu': 'wt_remote_storage_2_CPU_cycles',
                    'f-w-cpu-nvme': 'wt_remote_cpu_2_nvme_cycles',
                    'f-ip-remote-cpu':'data_remote_storage_2_CPU_cycles',
                    'f-ip-cpu-nvme': 'data_remote_cpu_2_nvme_cycles',
                    'f-ip-cpu-gpu': 'data_remote_cpu_2_gpu_cycles',
                    'f-nvme-cpu': 'wt_nvme_cpu_time_cycles',
                    'f-cpu-gpu': 'wt_cpu_gpu_time_cycles',
                    'f-allgather-su': 'comms_time_wt_cycles',
                    'f-allgather-so_pod': 'comms_scaleout_time_wt_cycles_pod',
                    'f-allgather-so_nic': 'comms_scaleout_time_wt_cycles_nic',
                    'f-comp': 'fwd_pass_comp_cycles'}

    bwd_w_sub_task = {'b-w-comp': 'wt_grad_comp_cycles',
                      'b-w-rs-su': 'comms_time_wtgrad_cycles',
                      'b-w-rs-so_pod': 'comms_scaleout_time_wt_grad_cycles_pod',
                      'b-w-rs-so_nic': 'comms_scaleout_time_wt_grad_cycles_nic',
                      'b-w-g-gpu-cpu': 'wt_grad_cpu_gpu_time_cycles',
                      'b-w-g-cpu-nvme': 'wt_grad_nvme_cpu_time_cycles'}

    bwd_d_sub_task = {'b-d-nvme-cpu': 'wt_nvme_cpu_time_cycles',
                      'b-d-cpu-gpu': 'wt_cpu_gpu_time_cycles',
                      'b-d-allgather-su': 'comms_time_wt_cycles',
                      'b-d-allgather-so_pod': 'comms_scaleout_time_wt_cycles_pod',
                      'b-d-allgather-so_nic': 'comms_scaleout_time_wt_cycles_nic',
                      'b-d-comp': 'inp_grad_comp_cycles'}

    opt_sub_task = {'o-nvme-cpu': 'wt_nvme_cpu_time_cycles',
                    'o-comp': 'fwd_pass_comp_cycles',
                    'o-g-cpu-nvme': 'wt_grad_nvme_cpu_time_cycles',
                    'o-w-cpu-remote':'wt_remote_storage_2_CPU_cycles'}

    # Workload parsing
    iteration = 1
    workload = Workload(network_name)
    start = Task('Start', TYPES.START, iterations = iteration)
    end = Task('End', TYPES.END)
    workload.add_tasks([start, end])
    conn = 1
    workload_cycles = 0
    cyclic_conn_1 = [None,None] # (storing updated weight cpu->nvme) -> (first layer fwd) || overlapping checkpointing ||
    cyclic_conn_2 = [None,None] #(final bwd-w layer's gpu->cpu) -> (input data read from remote) || overlapping remote data read ||
    cyclic_conn_3 = [None,None] # (previous epoch checkpoint) -> (current epoch opt starting) || based on paper ||
    wl_tasks = {}
    end_tasks = {}
    for layer in wl_json['nodes']:
        layer_pass = layer['data']['Layer']['l_pass']
        layer_name = layer['data']['Layer']['Layer Name']
        if 'fwd' in layer_pass or 'oth' in layer_pass:
            tasks, connections, conn, cycles = get_sub_tasks(layer, fwd_sub_task, pass2msg, conn, knobs)
            if 'fwd' in layer_pass and (not cyclic_conn_1[1]) and (not cyclic_conn_2[1]):
                cyclic_conn_1[1]= tasks[4] #first layer forward pass starting
                cyclic_conn_2[1] = tasks[2] #reading input from remote
                cyclic_conn_2[0] = tasks[-1]
            workload.tasks.extend(tasks)
            workload.connections.extend(connections)
            workload_cycles += cycles
        elif 'bwd-w' in layer_pass:
            tasks, connections, conn, cycles = get_sub_tasks(layer, bwd_w_sub_task, pass2msg, conn,knobs)
            workload.tasks.extend(tasks)
            workload.connections.extend(connections)
            workload_cycles += cycles
        elif 'bwd-d' in layer_pass:
            tasks, connections, conn, cycles = get_sub_tasks(layer, bwd_d_sub_task, pass2msg, conn,knobs)
            workload.tasks.extend(tasks)
            workload.connections.extend(connections)
            workload_cycles += cycles
        elif 'upd' in layer_pass:
            tasks, connections, conn, cycles = get_sub_tasks(layer, opt_sub_task, pass2msg, conn,knobs)
            if not cyclic_conn_3[0] and not cyclic_conn_1[0]:
                cyclic_conn_3 = [tasks[-1],tasks[0]] #next iteration nvme-cpu for optimization needs to wait until checkpoint of previous iteration completes
                cyclic_conn_1[0] = tasks[-2] #storing updated weight from cpu to nvme
            workload_cycles += cycles
            workload.tasks.extend(tasks)
            workload.connections.extend(connections)
            for cyclic_connection in [cyclic_conn_1,cyclic_conn_2,cyclic_conn_3]:
                #print("from:",cyclic_connection[0].name,"->","to:",cyclic_connection[1].name)
                connections,conn = make_cyclic_connection(cyclic_connection[0],cyclic_connection[1],conn)
                workload.connections.extend(connections)
            workload_cycles += cycles
        else:
            print("WARN: Unknown layer pass {}, skipping {}".format(layer_pass, layer_name))
            continue
        wl_tasks[layer_name] = (layer_pass, tasks)
        end_tasks[layer_name] = tasks[len(tasks) - 1]

    # external connections
    for src, dsts in successor_dict.items():
        src_pass, src_tasks = wl_tasks[src]
        t_src_tasks = [task for task in src_tasks if task.get_attribute('TASK_TYPE') != PVC_TASK_TYPE.COMM_SU]
        for dst in dsts:
            dst_pass, dst_tasks = wl_tasks[dst]

            # listOfSubtaskInSrc = [task.get_attribute("SUB_TASK_TYPE") for task in src_tasks]
            # listOfSubtaskInDst = [task.get_attribute("SUB_TASK_TYPE") for task in dst_tasks]
            # podFlag = False
            # nicFlag = False
            # for lst in listOfSubtaskInSrc:
            #     if "_pod" in lst:
            #         podFlag = True
            #     elif "_nic" in lst:
            #         nicFlag = True
            # if podFlag and nicFlag:
            #     t_src_tasks = [task for task in t_src_tasks if "_pod" not in task.get_attribute('SUB_TASK_TYPE')]
            #
            # podFlag = False
            # nicFlag = False
            # for lst in listOfSubtaskInDst:
            #     if "_pod" in lst:
            #         podFlag = True
            #     elif "_nic" in lst:
            #         nicFlag = True
            # if podFlag and nicFlag:
            #     dst_tasks = [task for task in dst_tasks if "_pod" not in task.get_attribute('SUB_TASK_TYPE')]


            # for task in dst_tasks:
            #     print(task.get_attribute("SUB_TASK_TYPE"))
            if src_pass == dst_pass or (src_pass == "fwd" and dst_pass == "oth"):
                if len(src_tasks) == len(dst_tasks):

                    listOfSubtaskInSrc = [task.get_attribute("SUB_TASK_TYPE") for task in src_tasks]
                    listOfSubtaskInDst = [task.get_attribute("SUB_TASK_TYPE") for task in dst_tasks]
                    podFlag = False
                    nicFlag = False
                    for lst in listOfSubtaskInSrc:
                        if "_pod" in lst:
                            podFlag = True
                        elif "_nic" in lst:
                            nicFlag = True
                    if podFlag and nicFlag:
                        t_src_tasks = [task for task in t_src_tasks if "_pod" not in task.get_attribute('SUB_TASK_TYPE')]

                    podFlag = False
                    nicFlag = False
                    for lst in listOfSubtaskInDst:
                        if "_pod" in lst:
                            podFlag = True
                        elif "_nic" in lst:
                            nicFlag = True
                    if podFlag and nicFlag:
                        dst_tasks = [task for task in dst_tasks if "_pod" not in task.get_attribute('SUB_TASK_TYPE')]

                    t_dst_tasks = [task for task in dst_tasks if task.get_attribute('TASK_TYPE') != PVC_TASK_TYPE.COMM_SO]
                    for src_task, dst_task in zip(t_src_tasks, t_dst_tasks):
                        workload.connect_tasks(str(conn), src_task, dst_task)
                        conn += 1
            elif (src_pass == "oth" and dst_pass == "bwd-d") or \
                    (src_pass == "bwd-d" and dst_pass == "bwd-w") or \
                    (src_pass == "bwd-w" and dst_pass == "upd"):
                src_taskn = src_tasks[len(src_tasks) - 1]
                dst_task1 = dst_tasks[0]
                workload.connect_tasks(str(conn), src_taskn, dst_task1)
                conn += 1

    for start_layer in start_layers:
        workload.connect_tasks(str(conn), start, wl_tasks[start_layer][1][0])
        conn += 1

    end_layers = list(predecessor_dict.keys() - successor_dict.keys())
    for end_layer in end_layers:
        workload.connect_tasks(str(conn), end_tasks[end_layer], end, put_samples=1, get_samples=counter*knobs['num_iterations'], buf_size=counter*knobs['num_iterations'])
        conn += 1

    '''
    end_layers = list(predecessor_dict.keys() - successor_dict.keys())
    for end_layer in end_layers:
        workload.connect_tasks(str(conn), end_tasks[end_layer], end, put_samples=1, get_samples=2, buf_size=4)
        conn += 1
    '''

    #workload.draw(os.path.basename(workload_json), view=False, format_='pdf', keep_gv=False)

    platform = get_platform(knobs, ref_period)

    # Simulating
    sim = SpeedSim(platform, workload, None)
    sim.set_system_scheduler(ZeroInfScheduler)
    # extension = sim.add_extension("Comms extension", CommsHandler)
    res = sim.simulate(knobs['num_iterations']*ref_period * (workload_cycles + 100))
    res = res.sort_values(axis='index', by=['START', 'FINISH'])

    res['START'] = res['START'] / 1000;
    res['FINISH'] = res['FINISH'] / 1000;
    res['DURATION'] = res['DURATION'] / 1000;

    res = add_verbose_cols(res, workload)
    res.rename(columns={"START": "START (ms)",
                        "FINISH": "FINISH (ms)",
                        "DURATION": "DURATION (ms)"},
               inplace=True)

    overlap_stats = get_overlap_stats(res)
    sim_summary = get_sim_summary(res)

    res.to_csv('res.csv')
    return OverlapSummaryReport(
        name="Overlap",
        info_df=overlap_stats,
        sim_summary=sim_summary,
        run_analysis=res
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--workload-json', type=str)
    parser.add_argument('--knobs-yaml', type=str)

    args = parser.parse_args(sys.argv[1:])
    from param.src.knobs import Knobs

    knobs = Knobs(args.knobs_yaml)
    speedsim_analysis_zero_inf(args.workload_json, knobs, True)
