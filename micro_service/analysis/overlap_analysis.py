import json
import sys
import os
import pandas
from typing import List
from numpy import arange

if os.name == "nt":
    path = '.\\speedsim\\'
else:
    path = './speedsim/'

if path not in sys.path:
    sys.path.append(path)


from report_objects import OverlapSummaryReport
from .fabsim_trace import convert2fabsim, FabsimParser
from asap.workload import Workload, Task, TYPES
from asap.ips import IP, ExecutingUnit, Driver, Port
from asap.hw import Clock
from asap.buses import Bus
from asap.memories import Memory
from asap.system_platform import Platform
from asap.schedulers import SystemScheduler
from asap.mapping import MappingEntity
from speedsim import SpeedSim
from post_processing.utils import AnalysisData

from .utils import interval2duration, merge_overlapping_intervals, get_overlap_duration


# Going throgh all the layers - create task of layer name
# Through each out/in tensor in each layer, save connections
def _get_source(link, workload_graph):
    source = int(link['source'])
    return workload_graph['nodes'][source]['label']

def _get_pass_from_id(node_id, workload_graph):
    return workload_graph['nodes'][node_id]['data']['Layer']['l_pass']

def _get_target(link, workload_graph):
    target = int(link['target'])
    return workload_graph['nodes'][target]['label']


def get_overlap_scaleup(df):
    df_overlap = df[(df["Task Type"] == "COMP") | (df["Task Type"] == "COMM")]
    intervals = list(zip(df_overlap["START"], df_overlap["FINISH"]))
    return sum(interval2duration(intervals)) - sum(interval2duration(merge_overlapping_intervals(intervals)))


def get_overlap_scaleout(df, subtype):
    # df_overlap = df[((df["Task Type"] == "COMP") | (df["Task Type"] == "COMM_SO_pod") | (df["Task Type"] == "COMM_SO_nic")) & (df["Task Sub Type"] == subtype)]
    df_overlap = df[
        (df["Task Type"] == "COMP") | ((df["Task Type"] == "COMM_SO_pod") | (df["Task Type"] == "COMM_SO_nic")) & (
                    df["Task Sub Type"] == subtype)]
    intervals = list(zip(df_overlap["START"], df_overlap["FINISH"]))
    return sum(interval2duration(intervals)) - sum(interval2duration(merge_overlapping_intervals(intervals)))


def disintegrate_interval(interval: pandas.Interval) -> List[pandas.Interval]:
    start = interval.left
    end = interval.right
    split = (end - start) / 21400
    disintegrated_intervals = []
    if start == end:
        return [interval]
    for _slice in arange(start, end, split):
        disintegrated_intervals.append(pandas.Interval(round(_slice, 4), round(_slice + split, 4)))
    return disintegrated_intervals


def get_overlapping_compute(interval, compute_intervals):
    for co_interval in compute_intervals:
        if co_interval.overlaps(interval):
            return co_interval
    return None


def set_duration(intervals):
    duration = 0
    for interval in intervals:
        duration += interval.length
    return duration


def get_overlap_scaleup_scaleout(df):
    df_overlap = df[(df["Task Type"] == "COMM_SO_nic") | (df["Task Type"] == "COMM_SO_pod")]
    df_overlap = df_overlap.sort_values(by=["START"], axis=0)
    scaleout_intervals = list(zip(df_overlap["START"], df_overlap["FINISH"]))
    scaleout_intervals = pandas.arrays.IntervalArray.from_tuples(scaleout_intervals)
    scaleout_intervals = [interval for interval in scaleout_intervals if interval.left != interval.right]

    df_overlap = df[(df["Task Type"] == "COMM")]
    df_overlap = df_overlap.sort_values(by=["START"], axis=0)
    scaleup_intervals = list(zip(df_overlap["START"], df_overlap["FINISH"]))
    scaleup_intervals = pandas.arrays.IntervalArray.from_tuples(scaleup_intervals)
    scaleup_intervals = [interval for interval in scaleup_intervals if interval.left != interval.right]

    df_overlap = df[(df["Task Type"] == "COMP")]
    df_overlap = df_overlap.sort_values(by=["START"], axis=0)
    compute_intervals = list(zip(df_overlap["START"], df_overlap["FINISH"]))

    compute_intervals = pandas.arrays.IntervalArray.from_tuples(compute_intervals)
    compute_intervals = [interval for interval in compute_intervals if interval.left != interval.right]

    duration = 0
    for su_interval in scaleup_intervals:
        for so_interval in scaleout_intervals:
            if su_interval.overlaps(so_interval):
                so_co_interval = get_overlapping_compute(so_interval, compute_intervals)
                su_co_interval = get_overlapping_compute(su_interval, compute_intervals)
                if not so_co_interval and su_co_interval:
                    com1 = set(disintegrate_interval(su_interval))
                    com2 = set(disintegrate_interval(so_interval))
                    cop = set(disintegrate_interval(su_co_interval))
                    duration += (set_duration(com1.intersection(com2) - cop))
                elif so_co_interval and not su_co_interval:
                    com1 = set(disintegrate_interval(su_interval))
                    com2 = set(disintegrate_interval(so_interval))
                    cop = set(disintegrate_interval(so_co_interval))
                    duration += (set_duration(com1.intersection(com2) - cop))
                elif so_co_interval and su_co_interval:
                    com1 = set(disintegrate_interval(su_interval))
                    com2 = set(disintegrate_interval(so_interval))
                    cop1 = set(disintegrate_interval(so_co_interval))
                    cop2 = set(disintegrate_interval(su_co_interval))
                    duration += (set_duration(com1.intersection(com2) - cop1 - cop2))
                else:
                    com1 = set(disintegrate_interval(su_interval))
                    com2 = set(disintegrate_interval(so_interval))
                    duration += (set_duration(com1.intersection(com2)))
    return duration

# KeyWords
SUCCESSORS = 'successors'
PREDECESSORS = 'predecessors'
FW = 'FW'
INP = 'INP'
WT = 'WT'
COMM = 'COMM'
COMM_FW = COMM + '_FW'
COMM_INP = COMM + '_INP'
COMM_WT = COMM + '_WT'
COMM_SO = COMM + '_SO'
COMM_SO_FW = COMM + '_SO_FW'
COMM_SO_INP = COMM + '_SO_INP'
COMM_SO_WT = COMM + '_SO_WT'
COMM_SO_FW_nic = COMM + '_SO_FW_nic'
COMM_SO_INP_nic = COMM + '_SO_INP_nic'
COMM_SO_WT_nic = COMM + '_SO_WT_nic'
COMM_SO_FW_pod = COMM + '_SO_FW_pod'
COMM_SO_INP_pod = COMM + '_SO_INP_pod'
COMM_SO_WT_pod = COMM + '_SO_WT_pod'

GPUs = 1
EX_UNITS_PER_GPU = 1



# Scheduler
class GPUScheduler(SystemScheduler):
    def __init__(self, system_mgr, properties=None, platform_scheduler=None):
        super().__init__(system_mgr, properties, platform_scheduler)
        self._gpus = self._get_ips(['GPU_{}'.format(gpu) for gpu in range(GPUs)])
        self._gpus_drivers = self._get_drivers(self._gpus)

    def _get_drivers(self, ips):
        drs = []
        for ip in ips:
            for dr in ip.drivers:
                drs.append(dr)
        return drs

    def _get_ips(self, names):
        ips = list()
        for ip in self._system_mgr.sys_platform.ips:
            #print(ip.name)
            if ip.name in names:
                ips.append(ip)
        return ips

    def schedule_task(self, task, resource=None):
        if resource is not None:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, resource)])
        if task.get_attribute('TASK_TYPE') is None or task.get_attribute('TASK_TYPE') != COMM:
            return self._platform_scheduler.schedule_task(task, [MappingEntity(task, self._gpus[0])])
        else:
            if str(vars(task)["_name"]).__contains__("_SO"):
                # check if we have separate driver for scaleout comms task if yes schedule on it else schedule on
                # scaleup driver
                scaleout_gpu_drivers = [MappingEntity(task, gpu) for gpu in self._gpus_drivers if
                                        str(vars(gpu)["_name"]).__contains__("COMMS_SO")]
                if len(scaleout_gpu_drivers) > 0:
                    return self._platform_scheduler.schedule_task(task,
                                                                  [MappingEntity(task, gpu) for gpu in
                                                                   self._gpus_drivers if
                                                                   str(vars(gpu)["_name"]).__contains__("COMMS_SO")])
                else:
                    return self._platform_scheduler.schedule_task(task,
                                                                  [MappingEntity(task, gpu) for gpu in
                                                                   self._gpus_drivers if
                                                                   not
                                                                   str(vars(gpu)["_name"]).__contains__("COMMS_SO")])
            else:
                return self._platform_scheduler.schedule_task(task,
                                                              [MappingEntity(task, gpu) for gpu in
                                                               self._gpus_drivers if
                                                               not
                                                               str(vars(gpu)["_name"]).__contains__("COMMS_SO")])

    def on_task_finish(self, task):
        self._platform_scheduler.on_task_finish(task)

def get_platform(knobs, ref_period):
    # HW
    platform = Platform('NNPT')
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

    platform.validate_platform()
    return platform


def speedsim_analysis(workload_json, knobs, include_timeline=False, trace_gen=True, network_name=None):
    # Loading workload as a dictionary from json file
    outFilePath = knobs['outFilePath']
    if outFilePath is None or len(outFilePath) <= 0:
        outFilePath = './modelzoo/'
    wl_json_file = workload_json
    wl_json_fd = open(wl_json_file, 'r')
    wl_json = json.load(wl_json_fd)

    workload_cycles = 0
    successor_dict = {}
    predecessor_dict = {}

    last_fwd_source = ""

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

    # add second iteration of fwd tasks,
    # this will act as bwd-fwd tasks
    if not knobs["data_parallel"] and not knobs["hybrid_model"] and knobs["enable_2x"]:
        first_fwd_source = list(successor_dict.keys() - predecessor_dict.keys())
        temp_keys = list(successor_dict.keys())
        for key in temp_keys:
            if "bwd_" not in key:
                if key != last_fwd_source:
                    # there mite be layers  which dont have successors
                    if key in successor_dict.keys():
                        successor_dict["2_" + key] = ["2_" + x for x in successor_dict[key]]
                    # there mite be layers  which dont have predecessors
                    if key in predecessor_dict.keys():
                        predecessor_dict["2_" + key] = ["2_" + x for x in predecessor_dict[key]]
                else:
                    if len(successor_dict[key]) == 1:
                        successor_dict["2_" + key] = successor_dict[key]
                        predecessor_dict["2_" + key] = ["2_" + x for x in predecessor_dict[key]]

                        predecessor_dict[successor_dict[key][0]] = ["2_" + key]
                        successor_dict[key] = ["2_" + x for x in first_fwd_source]
                        for x in first_fwd_source:
                            predecessor_dict["2_" + x] = [key]
                    else:
                        raise Exception("unable to construct taskgraph")

    # Going throgh all the layers - create task of layer name
    # Through each out/in tensor in each layer, save connections
    TASK_NAME_SEPARATOR = '__'
    ref_freq = knobs["frequency_in_Ghz"] * 1000  # 1.5GH = 1500Mhz = 0.000666us
    ref_period = 1 / ref_freq  # 1.5GH = 1500Mhz = 0.000666us

    msg_size_keys = {'comms_time_fwd_cycles': 'fwd_pass_msg_size',
                     'comms_scaleout_time_fwd_cycles_pod': 'fwd_pass_msg_size',
                     'comms_scaleout_time_fwd_cycles_nic': 'fwd_pass_msg_size',
                     'comms_time_inp_grad_cycles': 'inp_grad_msg_size',
                     'comms_scaleout_time_inp_cycles_pod': 'inp_grad_msg_size',
                     'comms_scaleout_time_inp_cycles_nic': 'inp_grad_msg_size',
                     'comms_time_wtgrad_cycles': 'wt_grad_msg_size',
                     'comms_scaleout_time_wt_cycles_nic': 'wt_grad_msg_size',
                     'comms_scaleout_time_wt_cycles_pod': 'wt_grad_msg_size'}

    comms_type_keys = {'comms_time_fwd_cycles': 'fwd_collective_comms_type',
                       'comms_scaleout_time_fwd_cycles_pod': 'fwd_collective_comms_type',
                       'comms_scaleout_time_fwd_cycles_nic': 'fwd_collective_comms_type',
                       'comms_time_inp_grad_cycles': 'inp_collective_comms_type',
                       'comms_scaleout_time_inp_cycles_pod': 'inp_collective_comms_type',
                       'comms_scaleout_time_inp_cycles_nic': 'inp_collective_comms_type',
                       'comms_time_wtgrad_cycles': 'wt_collective_comms_type',
                       'comms_scaleout_time_wt_cycles_pod': 'wt_collective_comms_type',
                       'comms_scaleout_time_wt_cycles_nic': 'wt_collective_comms_type'}

    fwd_layer_sub_tasks = {'fwd_pass_comp_cycles': FW,
                           'comms_time_fwd_cycles': COMM_FW,
                           'comms_scaleout_time_fwd_cycles_pod': COMM_SO_FW_pod,
                           'comms_scaleout_time_fwd_cycles_nic': COMM_SO_FW_nic,
                           'comms_scaleout_time_wt_cycles_pod': COMM_SO_WT_pod,
                           'comms_scaleout_time_wt_cycles_nic': COMM_SO_WT_nic}
    bwd_layer_sub_tasks = {'inp_grad_comp_cycles': INP,
                           'wt_grad_comp_cycles': WT,
                           'comms_time_inp_grad_cycles': COMM_INP,
                           'comms_time_wtgrad_cycles': COMM_WT,
                           'comms_scaleout_time_inp_cycles_pod': COMM_SO_INP_pod,
                           'comms_scaleout_time_inp_cycles_nic': COMM_SO_INP_nic,
                           'comms_scaleout_time_wt_cycles_pod': COMM_SO_WT_pod,
                           'comms_scaleout_time_wt_cycles_nic': COMM_SO_WT_nic}

    # Workload parsing
    workload = Workload('Resnet50')
    connections = dict()  # {layer -> {predeseccors: [layers], successors: [layers]}
    start = Task('Start', TYPES.START)
    end = Task('End', TYPES.END)
    workload.add_tasks([start, end])

    # Parsing layers, creating tasks and internal connections, saving external connections
    con = 0
    layers_num = len(wl_json['nodes'])
    for layer in wl_json['nodes']:
        layer_name = layer['data']['Layer']['Layer Name']
        layer_pass = layer['data']['Layer']['l_pass']
        try:
            weight = layer['data']['Layer']['Weight']
            input = layer['data']['Layer']['Input']
            output = layer['data']['Layer']['Output']
        except:
            weight = 0
            input = 0
            output = 0

        sub_tasks = dict()
        sub_task2 = dict()
        if "bwd" in layer_pass:
            for alias, sub_task in bwd_layer_sub_tasks.items():
                processing_cycles = float(layer['data']['Layer'][alias])
                workload_cycles += processing_cycles
                if processing_cycles > 0 or not sub_task.startswith(COMM):
                    if sub_task.startswith(COMM):
                        proc = Task(layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                    processing_cycles=processing_cycles,
                                    msg_size=float(layer['data']['Layer'][msg_size_keys[alias]]),
                                    comms_type=layer['data']['Layer'][comms_type_keys[alias]],
                                    layer_pass=layer_pass, weight=weight, input=input, output=output)
                    else:
                        proc = Task(layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                    processing_cycles=processing_cycles,
                                    layer_pass=layer_pass, weight=weight, input=input, output=output)
                    if sub_task.startswith(COMM):
                        proc.attach_attribute('TASK_TYPE', COMM)
                    sub_tasks[sub_task] = proc

                    workload.add_task(proc)

            if COMM_INP in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[INP], sub_tasks[COMM_INP])
                con += 1
                if COMM_SO_INP_pod  in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_INP], sub_tasks[COMM_SO_INP_pod])
                    con += 1
                    if COMM_SO_INP_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_INP_pod], sub_tasks[COMM_SO_INP_nic])
                        con += 1
                elif COMM_SO_INP_nic  in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_INP], sub_tasks[COMM_SO_INP_nic])
                    con += 1
            elif COMM_SO_INP_pod in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[INP], sub_tasks[COMM_SO_INP_pod])
                con += 1
                if COMM_SO_INP_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_INP_pod], sub_tasks[COMM_SO_INP_nic])
                    con += 1

            new_end = Task('End_of_' + layer_name + '_WT', TYPES.END)
            workload.add_task(new_end)

            if COMM_WT in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[WT], sub_tasks[COMM_WT])
                con += 1
                if COMM_SO_WT_pod in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_WT], sub_tasks[COMM_SO_WT_pod])
                    con += 1
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_nic], new_end)
                        con += 1
                elif COMM_SO_WT_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_WT], sub_tasks[COMM_SO_WT_nic])
                    con += 1
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_nic], new_end)
                    con += 1
                else:
                    workload.connect_tasks(str(con), sub_tasks[COMM_WT], new_end)
                    con += 1
            elif COMM_SO_WT_pod in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[WT], sub_tasks[COMM_SO_WT_pod])
                con += 1
                if COMM_SO_WT_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                    con += 1
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_nic], new_end)
                    con += 1
            elif COMM_SO_WT_nic in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[WT], sub_tasks[COMM_SO_WT_nic])
                con += 1
                workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_nic], new_end)
                con += 1
            elif WT in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[WT], new_end)
                con += 1
            else:
                print("Could not connect {}".format(new_end.name))

            if WT in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[INP], sub_tasks[WT])
                con += 1

            # new_end = Task('End_of_' + layer_name + 'COMM_SO', TYPES.END)
            # workload.add_task(new_end)
            # workload.connect_tasks(str(con), sub_tasks[COMM_SO], new_end)
            # con += 1

        else:
            for alias, sub_task in fwd_layer_sub_tasks.items():

                processing_cycles = float(layer['data']['Layer'][alias])
                workload_cycles += processing_cycles
                # comms which have 0 processing cycles to be ignored,
                # INP and WT even though they have 0 processing cycle, create task related to that
                if processing_cycles > 0 or not sub_task.startswith(COMM):
                    if sub_task.startswith(COMM):
                        proc = Task(layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                    processing_cycles=processing_cycles,
                                    msg_size=float(layer['data']['Layer'][msg_size_keys[alias]]),
                                    comms_type=layer['data']['Layer'][comms_type_keys[alias]],
                                    layer_pass=layer_pass, weight=weight, input=input, output=output)
                    else:
                        proc = Task(layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                    processing_cycles=processing_cycles,
                                    layer_pass=layer_pass, weight=weight, input=input, output=output)
                    if sub_task.startswith(COMM):
                        proc.attach_attribute('TASK_TYPE', COMM)
                    sub_tasks[sub_task] = proc
                    workload.add_task(proc)

                    if not knobs["data_parallel"] and not knobs["hybrid_model"] and knobs["enable_2x"]:
                        if sub_task.startswith(COMM):
                            proc2 = Task("2_" + layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                         processing_cycles=processing_cycles,
                                         msg_size=float(layer['data']['Layer'][msg_size_keys[alias]]),
                                         comms_type=layer['data']['Layer'][comms_type_keys[alias]],
                                         layer_pass=layer_pass, weight=weight, input=input, output=output)
                        else:
                            proc2 = Task("2_" + layer_name + TASK_NAME_SEPARATOR + sub_task, TYPES.PROC,
                                         processing_cycles=processing_cycles,
                                         layer_pass=layer_pass, weight=weight, input=input, output=output)
                        if sub_task.startswith(COMM):
                            proc2.attach_attribute('TASK_TYPE', COMM)
                        sub_task2[sub_task] = proc2
                        workload.add_task(proc2)

            if COMM_FW in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[FW], sub_tasks[COMM_FW])
                con += 1
                if COMM_SO_FW_pod in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_FW], sub_tasks[COMM_SO_FW_pod])
                    con += 1
                    if COMM_SO_WT_pod in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_WT_pod])
                        con += 1
                        if COMM_SO_WT_nic in sub_tasks.keys():
                            workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                            con += 1
                    elif COMM_SO_FW_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_FW_nic])
                        con += 1
                        if COMM_SO_WT_nic in sub_tasks.keys():
                            workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_nic], sub_tasks[COMM_SO_WT_nic])
                            con += 1
                    elif COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_FW_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_FW], sub_tasks[COMM_SO_FW_nic])
                    con += 1
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_nic], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                else:
                    if COMM_SO_WT_pod in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_FW], sub_tasks[COMM_SO_WT_pod])
                        con += 1
                        if COMM_SO_WT_nic in sub_tasks.keys():
                            workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                            con += 1
                    else:
                        if COMM_SO_WT_nic in sub_tasks.keys():
                            workload.connect_tasks(str(con), sub_tasks[COMM_FW], sub_tasks[COMM_SO_WT_nic])
                            con += 1
            elif COMM_SO_FW_pod in sub_tasks.keys():
                workload.connect_tasks(str(con), sub_tasks[FW], sub_tasks[COMM_SO_FW_pod])
                con += 1
                if COMM_SO_WT_pod in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_WT_pod])
                    con += 1
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_FW_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_FW_nic])
                    con += 1
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_nic], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_WT_nic in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[COMM_SO_FW_pod], sub_tasks[COMM_SO_WT_nic])
                    con += 1
            else:
                if COMM_SO_WT_pod in sub_tasks.keys():
                    workload.connect_tasks(str(con), sub_tasks[FW], sub_tasks[COMM_SO_WT_pod])
                    con += 1
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[COMM_SO_WT_pod], sub_tasks[COMM_SO_WT_nic])
                        con += 1
                else:
                    if COMM_SO_WT_nic in sub_tasks.keys():
                        workload.connect_tasks(str(con), sub_tasks[FW], sub_tasks[COMM_SO_WT_nic])
                        con += 1

            if COMM_FW in sub_task2.keys():
                workload.connect_tasks("2_" + str(con), sub_task2[FW], sub_task2[COMM_FW])
                con += 1
                if COMM_SO_FW_pod in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[COMM_FW], sub_task2[COMM_SO_FW_pod])
                    con += 1
                    if COMM_SO_WT_pod in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_WT_pod])
                        con += 1
                        if COMM_SO_WT_nic in sub_task2.keys():
                            workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_WT_pod],sub_task2[COMM_SO_WT_nic])
                            con += 1
                    elif COMM_SO_FW_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_FW_nic])
                        con += 1
                        if COMM_SO_WT_nic in sub_task2.keys():
                            workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_nic], sub_task2[COMM_SO_WT_nic])
                            con += 1
                    elif COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_FW_nic in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[COMM_FW], sub_task2[COMM_SO_FW_nic])
                    con += 1
                    if COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_nic], sub_task2[COMM_SO_WT_nic])
                        con += 1
                else:
                    if COMM_SO_WT_pod in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_FW], sub_task2[COMM_SO_WT_pod])
                        con += 1
                        if COMM_SO_WT_nic in sub_task2.keys():
                            workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_WT_pod], sub_task2[COMM_SO_WT_nic])
                            con += 1
                    else:
                        if COMM_SO_WT_nic in sub_task2.keys():
                            workload.connect_tasks("2_" + str(con), sub_task2[COMM_FW], sub_task2[COMM_SO_WT_nic])
                            con += 1
            elif COMM_SO_FW_pod in sub_task2.keys():
                workload.connect_tasks("2_" + str(con), sub_task2[FW], sub_task2[COMM_SO_FW_pod])
                con += 1
                if COMM_SO_WT_pod in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_WT_pod])
                    con += 1
                    if COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_WT_pod], sub_task2[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_FW_nic in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_FW_nic])
                    con += 1
                    if COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_nic], sub_task2[COMM_SO_WT_nic])
                        con += 1
                elif COMM_SO_WT_nic in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_FW_pod], sub_task2[COMM_SO_WT_nic])
                    con += 1
            else:
                if COMM_SO_WT_pod in sub_task2.keys():
                    workload.connect_tasks("2_" + str(con), sub_task2[FW], sub_task2[COMM_SO_WT_pod])
                    con += 1
                    if COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[COMM_SO_WT_pod], sub_task2[COMM_SO_WT_nic])
                        con += 1
                else:
                    if COMM_SO_WT_nic in sub_task2.keys():
                        workload.connect_tasks("2_" + str(con), sub_task2[FW], sub_task2[COMM_SO_WT_nic])
                        con += 1

        # Retreiving successors connections
        layer_connections = connections.get(layer_name, dict())
        successors = layer_connections.get(SUCCESSORS, [])
        if layer_name in successor_dict.keys():
            successors.extend(successor_dict[layer_name])
        layer_connections[SUCCESSORS] = successors

        # Retreiving predecessors connections
        predecessors = layer_connections.get(PREDECESSORS, [])
        if layer_name in predecessor_dict.keys():
            predecessors.extend(predecessor_dict[layer_name])
        layer_connections[PREDECESSORS] = predecessors
        connections[layer_name] = layer_connections

        if "bwd" not in layer_pass and not knobs["data_parallel"] and not knobs["hybrid_model"]:
            layer_connections2 = connections.get("2_" + layer_name, dict())
            successors = layer_connections2.get(SUCCESSORS, [])
            if "2_" + layer_name in successor_dict.keys():
                successors.extend(successor_dict["2_" + layer_name])
            layer_connections2[SUCCESSORS] = successors

            predecessors = layer_connections2.get(PREDECESSORS, [])
            if "2_" + layer_name in predecessor_dict.keys():
                predecessors.extend(predecessor_dict["2_" + layer_name])
            layer_connections2[PREDECESSORS] = predecessors
            connections["2_" + layer_name] = layer_connections2

    # External connections
    for layer, layer_connections in connections.items():
        # Successors connections
        if "bwd_" not in layer:
            layer_fw_so_comm_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_FW_nic)
            if layer_fw_so_comm_t is None:
                layer_fw_so_comm_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_FW_pod)
            if layer_fw_so_comm_t is None:
                layer_fw_so_comm_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_FW)
            if layer_fw_so_comm_t is None:
                layer_fw_so_comm_t = workload.get_task(layer + TASK_NAME_SEPARATOR + FW)
            successors = layer_connections.get(SUCCESSORS, [])
            for successor in successors:
                if "bwd_" not in successor:
                    successor_fw_t = workload.get_task(successor + TASK_NAME_SEPARATOR + FW)
                    workload.connect_tasks(str(con), layer_fw_so_comm_t, successor_fw_t);
                    con += 1
                else:
                    successor_inp_t = workload.get_task(successor + TASK_NAME_SEPARATOR + INP)
                    if layer_fw_so_comm_t and successor_inp_t:
                        workload.connect_tasks(str(con), layer_fw_so_comm_t, successor_inp_t)
                        con += 1
        else:
            layer_comm_so_inp_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_INP_nic)
            if layer_comm_so_inp_t is None:
                layer_comm_so_inp_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_INP_pod)
            if layer_comm_so_inp_t is None:
                layer_comm_so_inp_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_INP)
            if layer_comm_so_inp_t is None:
                layer_comm_so_inp_t = workload.get_task(layer + TASK_NAME_SEPARATOR + INP)
            successors = layer_connections.get(SUCCESSORS, [])
            for successor in successors:
                if "bwd_" in successor:  # redudant check bwd layer successors are always
                    successor_inp_t = workload.get_task(successor + TASK_NAME_SEPARATOR + INP)
                    workload.connect_tasks(str(con), layer_comm_so_inp_t, successor_inp_t)
                    con += 1
                else:
                    # this is last optimizer layer, which should get triggered after
                    # all sub tasks have to be executed before optimizer can kick in
                    # as COMM_SO_WT is the last subtask in this TE graph
                    layer_comm_so_wt_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_WT_nic)
                    if layer_comm_so_wt_t is None:
                        layer_comm_so_wt_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_SO_WT_pod)
                    if layer_comm_so_wt_t is None:
                        layer_comm_so_wt_t = workload.get_task(layer + TASK_NAME_SEPARATOR + COMM_WT)
                    if layer_comm_so_wt_t is None:
                        layer_comm_so_wt_t = workload.get_task(layer + TASK_NAME_SEPARATOR + WT)
                    successor_fw_t = workload.get_task(successor + TASK_NAME_SEPARATOR + FW)
                    workload.connect_tasks(str(con), layer_comm_so_wt_t, successor_fw_t)
                    con += 1

    # layers that dont have predecessors dont have any triggering point
    # so they have to be triggered from start
    start_layers = list(successor_dict.keys() - predecessor_dict.keys())
    for start_layer in start_layers:
        start_layer_fw = workload.get_task(start_layer + TASK_NAME_SEPARATOR + FW)
        workload.connect_tasks(str(con), start, start_layer_fw)
        con += 1

    end_layers = list(predecessor_dict.keys() - successor_dict.keys())
    for end_layer in end_layers:
        end_layer_comm_fw = workload.get_task(end_layer + TASK_NAME_SEPARATOR + COMM_FW)
        if end_layer_comm_fw is None:
            end_layer_comm_fw = workload.get_task(end_layer + TASK_NAME_SEPARATOR + FW)
        workload.connect_tasks(str(con), end_layer_comm_fw, end)
        con += 1

    if include_timeline:
        workload.draw(os.path.basename(wl_json_file), view=False, format_='pdf', keep_gv=False)

    if trace_gen:
        ngpu = knobs["num_pvc"] * knobs["num_tiles_per_pvc"]
        tiles_per_node = ngpu / knobs["num_PVC_per_host"]
        mp = knobs["model_split"]
        dp = ngpu / mp
        # FIXME: fix the nuber of nodes parameter
        convert2fabsim(workload, network_name, "{}.json".format(network_name), 1.5, mp, dp,
                       knobs["num_PVC_per_host"], tiles_per_node, knobs["data_parallel"])

    platform = get_platform(knobs, ref_period)

    # Simulating
    sim = SpeedSim(platform, workload, None)
    sim.set_system_scheduler(GPUScheduler)
    # extension = sim.add_extension("Comms extension", CommsHandler)
    res = sim.simulate(ref_period * workload_cycles * 4)
    res = res.sort_values(axis='index', by=['START', 'FINISH'])

    return overlap_report(res, knobs, workload)


def overlap_report(res, knobs, workload):

    res['START'] = res['START'] / 1000;
    res['FINISH'] = res['FINISH'] / 1000;
    res['DURATION'] = res['DURATION'] / 1000;

    clear_results = res

    # additional columns to results

    res["Task Type"] = ['COMM_SO_nic' if 'nic' in x else ('COMM_SO_pod' if 'pod' in x else ('COMM' if 'COMM' in x else 'COMP')) for x in
                        res['TRANSITION']]
    res["Task Sub Type"] = ['FW' if (x.endswith('_FW') or x.endswith('_FW_nic') or x.endswith('_FW_pod')) else ('INP' if (x.endswith('_INP') or x.endswith('_INP_pod') or x.endswith('_INP_nic')) else 'WT') for x in
                            res['TRANSITION']]
    res["Message Size (bytes)"] = [workload.get_task(x).get_attribute("msg_size", 'NA') for x in res['TRANSITION']]

    duration = res.groupby(['Task Type', 'Task Sub Type']).sum().to_dict()['DURATION']

    def get_subkey_sum(val_dict, subkey):
        # if subkey occurs in key of dict, then consider value for sum
        sum = 0
        for key in val_dict.keys():
            if subkey in list(key):
                sum += val_dict[key]
        return sum

    total_compute_time = get_subkey_sum(duration, 'COMP')
    scaleup_time = get_subkey_sum(duration, 'COMM')
    scaleout_wt_time_nic = duration[('COMM_SO_nic', 'WT')] if ('COMM_SO_nic', 'WT') in duration.keys() else 0
    scaleout_wt_time_pod = duration[('COMM_SO_pod', 'WT')] if ('COMM_SO_pod', 'WT') in duration.keys() else 0
    scaleout_wt_time = scaleout_wt_time_nic+scaleout_wt_time_pod

    scaleout_inp_time_nic = duration[('COMM_SO_nic', 'INP')] if ('COMM_SO_nic', 'INP') in duration.keys() else 0
    scaleout_inp_time_pod = duration[('COMM_SO_pod', 'INP')] if ('COMM_SO_pod', 'INP') in duration.keys() else 0
    scaleout_inp_time = scaleout_inp_time_nic+scaleout_inp_time_pod

    scaleout_fw_time_nic = duration[('COMM_SO_nic', 'FW')] if ('COMM_SO_nic', 'FW') in duration.keys() else 0
    scaleout_fw_time_pod = duration[('COMM_SO_pod', 'FW')] if ('COMM_SO_pod', 'FW') in duration.keys() else 0
    scaleout_fw_time = scaleout_fw_time_nic+scaleout_fw_time_pod
    print("scaleout_fw_time_nic:",scaleout_fw_time_nic)
    print("scaleout_fw_time_pod:", scaleout_fw_time_pod)

    overlap_time = (1 - knobs["max_overlap"]) * (
            scaleup_time + scaleout_wt_time + scaleout_inp_time + scaleout_fw_time) + \
                   (AnalysisData.instance.simulation_time / 1000)
    overlap_time_scaleup = (1 - knobs["max_overlap"]) * scaleup_time + scaleup_time - get_overlap_scaleup(
        res)
    overlap_time_scaleout_inp = (1 - knobs["max_overlap"]) * scaleout_inp_time + \
                                scaleout_inp_time - get_overlap_scaleout(res, "INP")
    overlap_time_scaleout_wt = (1 - knobs["max_overlap"]) * scaleout_wt_time + \
                               scaleout_wt_time - get_overlap_scaleout(res, "WT")

    if knobs['so_overlap_scaleup']:
        total_sim_time_str = "Total time with overlap (Compute with Comms, Scaleout with Scaleup) per tile(ms)"
    else:
        total_sim_time_str = "Total time with overlap (Compute with Comms) per tile(ms)"

    info_lst = [["Total Compute time per tile(ms)", total_compute_time],
                ["Scale Up no overlap time (ms)", scaleup_time if scaleup_time > 0 else 0],
                ["Scale Up overlap with Compute, per tile(ms)",
                 overlap_time_scaleup if overlap_time_scaleup > 0 else 0],

                ["Scale Out FW time (ms)", scaleout_fw_time if scaleout_fw_time > 0 else scaleout_fw_time],
                ["Scale Out FW time pod (ms)",
                 scaleout_fw_time_pod if scaleout_fw_time_pod > 0 else scaleout_fw_time_pod],
                ["Scale Out FW time nic (ms)",
                 scaleout_fw_time_nic if scaleout_fw_time_nic > 0 else scaleout_fw_time_nic],
                ["Scale Out No overlap, Model parallel (INP) time, per tile(ms)",
                 scaleout_inp_time if scaleout_inp_time > 0 else 0],
                ["Scale Out No overlap, Model parallel (INP) time pod, per tile(ms)",
                 scaleout_inp_time_pod if scaleout_inp_time_pod > 0 else 0],
                ["Scale Out No overlap, Model parallel (INP) time nic, per tile(ms)",
                 scaleout_inp_time_nic if scaleout_inp_time_nic > 0 else 0],
                ["Scale Out overlap with Compute, Model parallel (INP) time, per tile(ms)",
                 overlap_time_scaleout_inp if overlap_time_scaleout_inp > 0 else 0],

                ["Scale Out No overlap, Data parallel (WT) time, per tile(ms)",
                 scaleout_wt_time if scaleout_wt_time > 0 else 0],
                ["Scale Out No overlap, Data parallel (WT) time pod, per tile(ms)",
                 scaleout_wt_time_pod if scaleout_wt_time_pod > 0 else 0],
                ["Scale Out No overlap, Data parallel (WT) time nic, per tile(ms)",
                 scaleout_wt_time_nic if scaleout_wt_time_nic > 0 else 0],
                ["Scale Out overlap with Compute, Data parallel (WT) time, per tile(ms)",
                 overlap_time_scaleout_wt if overlap_time_scaleout_wt > 0 else 0],

                ["Total Scaleup comm overlap with Scaleout comm and not with Compute (ms)",
                 get_overlap_scaleup_scaleout(res)],
                ["Total time without overlap per tile (ms)", res['DURATION'].sum()],
                [total_sim_time_str, overlap_time],
                ["Scaling efficiency (%)", total_compute_time / overlap_time * 100]]
    if knobs["data_parallel"]:
        info_lst.append(["Throughput compute only per tile", knobs["batch_size"] * 1000 / total_compute_time])
        info_lst.append(["Throughput full overlap per tile", knobs["batch_size"] * 1000 / overlap_time])
        info_lst.append(["Throughput no overlap per tile", knobs["batch_size"] * 1000 / res['DURATION'].sum()])
        if knobs["so_enabled"]:
            info_lst.append(["Throughput full overlap", knobs["batch_size"] * 1000 / overlap_time
                             * knobs["num_tiles_per_pvc"] * knobs["num_pvc"]])
        else:
            info_lst.append(["Throughput full overlap", knobs["batch_size"] * 1000 / overlap_time
                             * knobs["num_tiles_per_pvc"] * knobs["num_PVC_per_host"]])

    else:
        if knobs["so_enabled"]:
            total_dp = knobs["num_pvc"] * knobs["num_tiles_per_pvc"] / knobs["model_split"]
        else:
            total_dp = knobs["num_tiles_per_pvc"] * knobs["num_PVC_per_host"] / knobs["model_split"]
        throughput_compute_only_per_dp = knobs["batch_size"] * 1000 / total_compute_time
        throughput_full_overlap_per_dp = knobs["batch_size"] * 1000 / overlap_time
        throughput_no_overlap_per_dp = knobs["batch_size"] * 1000 / res['DURATION'].sum()
        info_lst.append(["Throughput compute only per tile", throughput_compute_only_per_dp / knobs["model_split"]])
        info_lst.append(["Throughput full overlap per tile", throughput_full_overlap_per_dp / knobs["model_split"]])
        info_lst.append(["Throughput no overlap per tile", throughput_no_overlap_per_dp / knobs["model_split"]])
        info_lst.append(["Throughput full overlap", throughput_full_overlap_per_dp * total_dp])


    info_df = pandas.DataFrame(info_lst, columns=["Metric", "Value"])

    clear_results.rename(columns={"START": "START (ms)", "FINISH": "FINISH (ms)", "DURATION": "DURATION (ms)"},
                         inplace=True)

    return OverlapSummaryReport(
        name="Overlap",
        info_df=info_df,
        run_analysis=clear_results
    )


def fabsim_analysis(fabsim_trace, fabsim_scaleup_run_log, fabsim_scaleout_run_log, knobs, network_name):

    wl_json = json.load(open(fabsim_trace, 'r'))
    fs_scaleup_parser = FabsimParser(fabsim_scaleup_run_log)
    fs_scaleout_parser = FabsimParser(fabsim_scaleout_run_log)
    # Workload parsing
    workload = Workload(network_name)
    connections = dict()  # {layer -> {predeseccors: [layers], successors: [layers]}
    start = Task('Start', TYPES.START)
    end = Task('End', TYPES.END)
    workload.add_tasks([start, end])
    ref_freq = knobs["frequency_in_Ghz"] * 1000  # 1.5GH = 1500Mhz = 0.000666us
    ref_period = 1 / ref_freq
    workload_cycles = 0
    connections_count = 0

    for layer in wl_json['Layers']:
        layer_pass = layer['Pass']
        if "_SO" in layer['LayerName'] and fs_scaleout_parser is not None:
            fabsim_task = fs_scaleout_parser.task_list[layer['LayerName']]
        else:
            fabsim_task = fs_scaleup_parser.task_list[layer['LayerName']]
        if fabsim_task.task_type == 'comm':
            workload_cycles += (fabsim_task.cycle * ref_freq/1000)
            proc = Task(layer['LayerName'], TYPES.PROC,
                        processing_cycles=fabsim_task.cycle * ref_freq/1000,
                        msg_size=fabsim_task.msg_size,
                        comms_type=fabsim_task.task_type,
                        layer_pass=layer_pass)
            proc.attach_attribute('TASK_TYPE', 'COMM')
        else:
            workload_cycles += layer["ComputeCycles"]
            proc = Task(layer['LayerName'], TYPES.PROC,
                        processing_cycles=layer["ComputeCycles"],
                        msg_size=fabsim_task.msg_size,
                        comms_type=fabsim_task.task_type,
                        layer_pass=layer_pass)
        workload.add_task(proc)

    for layer in wl_json['Layers']:
        dependency = layer['Dependency']
        if dependency:
            for predecessor in dependency:
                pred = workload.get_task(predecessor)
                proc = workload.get_task(layer['LayerName'])
                workload.connect_tasks(str(connections_count), pred, proc)
                connections_count += 1
        else:
            proc = workload.get_task(layer['LayerName'])
            workload.connect_tasks(str(connections_count), start, proc)
            connections_count += 1

    workload.connect_tasks(str(connections_count), proc, end)

    platform = get_platform(knobs, ref_period)

    sim = SpeedSim(platform, workload, None)
    sim.set_system_scheduler(GPUScheduler)
    # extension = sim.add_extension("Comms extension", CommsHandler)
    res = sim.simulate(workload_cycles * 4)

    return overlap_report(res, knobs, workload)

