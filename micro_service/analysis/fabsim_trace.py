import json
import re
from collections import namedtuple


def coroutine(func):
    """
    co routine starter function
    :param func:
    :return:
    """

    def starter(*args, **kwargs):
        cr = func(*args, **kwargs)
        next(cr)
        return cr

    return starter


class FabsimParser:
    FabsimTask = namedtuple('FabsimTask', ['task_type', 'layer', 'cycle', 'is_mp', 'msg_size'])

    def reader(self, thefile, target):
        for line in thefile:
            target.send(line)

    @coroutine
    def starts_with(self, pattern, target):
        while True:
            line = (yield)
            if line.startswith(pattern):
                target.send(line)

    @coroutine
    def grep(self, patterns_targets_dict):
        while True:
            line = (yield)
            for target, pattern in patterns_targets_dict.items():
                if any(x in line for x in pattern):
                    target.send(line)

    def remove_white_space(self, inp_list):
        ret_list = []
        for item in inp_list:
            if len(item):
                ret_list.append(item)
        return ret_list

    @coroutine
    def compute(self):
        _compute_cycle_idx = 6
        _compute_layer_idx = 9
        while True:
            line = (yield)
            task = self.remove_white_space(re.split(":| ", line.rstrip("\n")))
            layer = task[_compute_layer_idx]
            cycle = float(task[_compute_cycle_idx])
            self._task_list[layer] = FabsimParser.FabsimTask(task_type='compute', layer=layer, cycle=cycle, is_mp=False,
                                                       msg_size=0)

    @coroutine
    def comm_enter(self):
        _comm_msg_size = 8
        _comm_is_mp = 10
        _comm_layer = 13
        _comm_time = 8
        while True:
            line = (yield)
            task = self.remove_white_space(re.split(":| ", line.rstrip("\n")))
            layer = task[_comm_layer]
            msg_size = float(task[_comm_msg_size])
            is_mp = float(task[_comm_is_mp])
            line = (yield)
            task = self.remove_white_space(re.split(":| ", line.rstrip("\n")))
            time = float(task[_comm_time])
            self._task_list[layer] = FabsimParser.FabsimTask(task_type='comm', layer=layer, cycle=time, is_mp=bool(is_mp),
                                                       msg_size=msg_size)

    def __init__(self, run_log):
        self._task_list = {}
        with open(run_log) as f:
            self.reader(f, self.starts_with("process_id: 0",
                                            self.grep({self.compute(): ["performing"],
                                                       self.comm_enter(): ["entering", "exiting"]})))

    @property
    def task_list(self):
        return self._task_list


def convert2fabsim(workload, workload_name, trace_filename, frequency=1.5, mp=0, dp=0,
                   num_nodes=1, tiles_per_node=1, data_parallel=True):
    """
    Convert workload into fabsim acceptable trace
    :param workload: speedsim workload
    :param workload_name:
    :param trace_filename:
    :param frequency:
    :param mp:
    :param dp:
    :param num_nodes:
    :param tiles_per_node:
    :return:
    """

    def max_uint32(bytes):
        if bytes > 4294967295:
            return bytes/2
        return bytes

    def isvalid_task(task):
        if "end" not in task.name \
                and "End" not in task.name \
                and "start" not in task.name \
                and "Start" not in task.name:
            return True
        return False

    def _get_predecessors(task):
        predecessors = []
        for connection in workload.connections:
            if connection.target.name == task.name and isvalid_task(task):
                predecessors.append(connection.source.name)
        if not len(predecessors):
            return "null"
        return predecessors

    def _get_layer_pass(task):
        _pass = task.get_attribute("layer_pass", None).upper()
        if _pass == "FWD" or _pass == "BWD":
            return _pass
        else:
            return "BWD"

    layers = []
    layer_num = 0
    for idx, task in enumerate(workload.tasks, 0):
        if isvalid_task(task):
            layer = {"Pass": _get_layer_pass(task), "LayerNum": layer_num, "LayerName": task.name,
                     "Dependency": _get_predecessors(task),
                     "FreqGHz": frequency,
                     "Weights": max_uint32(task.get_attribute("weight") / 2),
                     "WeightsBytes": max_uint32(task.get_attribute("weight")),
                     "Input": max_uint32(task.get_attribute("input") / 2),
                     "InputBytes": max_uint32(task.get_attribute("input")),
                     "Output": max_uint32(task.get_attribute("output") / 2),
                     "OutputBytes": max_uint32(task.get_attribute("output"))}
            layer_num += 1
            if "COMM" in task.name:
                layer["CommCycles"] = task.processing_cycles
                layer["MsgSize"] = task.get_attribute("msg_size")
                layer["CommType"] = task.get_attribute("comms_type")
                if layer["WeightsBytes"] != layer["MsgSize"]:
                    layer["WeightsBytes"] = layer["MsgSize"]
                if "_WT" in layer["LayerName"]:
                    layer["MP"] = "False"
                else:
                    layer["MP"] = "True"
                    layer["Weights"] = 0
                    layer["WeightsBytes"] = 0
                    #print(task.name)
                    assert (layer["OutputBytes"])
                layer["OPTYPE"] = "comm"
                if data_parallel:
                    if "_SO" in layer["LayerName"]:
                        layer["MsgSize"] = layer["MsgSize"] / tiles_per_node
                        layer["WeightsBytes"] = layer["WeightsBytes"] / tiles_per_node
                else:
                    if "_SO" in layer["LayerName"] and ("_INP" in layer["LayerName"] or "_FW" in layer["LayerName"]):
                        layer["OutputBytes"] = layer["OutputBytes"] / tiles_per_node
            else:
                layer["Input"] = 50
                layer["InputBytes"] = 100
                layer["Output"] = 50
                layer["OutputBytes"] = 100
                layer["ComputeCycles"] = task.processing_cycles
                layer["OPTYPE"] = "compute"
            layers.append(layer)

    trace_dict = {}
    trace_dict["Model"] = {"Name": workload_name}
    trace_dict["System"] = {"Name": "T{}_MP{}_DP{}".format(mp * dp, mp, dp), "MP": mp, "DP": dp, "nCPU": mp * dp,
                            "nNodes": num_nodes, "nTilesNode": tiles_per_node}
    trace_dict["Layers"] = layers

    with open(trace_filename, 'w') as fp:
        fp.write(json.dumps(trace_dict, indent=4))
