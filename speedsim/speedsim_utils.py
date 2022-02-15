import logging
import math
import os
import platform
import subprocess
import sys
from copy import deepcopy
from math import gcd

from asap.strings import (AND, END_TRIGGER, NAME_SEPARATOR, OR, RESOURCE,
                          START_TRIGGER, TASK, TASK_SPLIT_COUNT, TRIGGER_IN,
                          TRIGGER_OUT, TYPE, WLTASK_NAME, MappingDesc,
                          ResourceDesc, TaskMetaData)
from asap.workload import TYPES, Task
from pnets.attributes import BUFFER_SIZE, INIT_COUNT, WEIGHT
from pnets.pn_model import PnmlModel
from pnets.simulation import ResourceState
from strings import SPEEDSIM_DEBUG

LINUX = "Linux"
WINDOWS = "Windows"
TOOL = "SpeedSim"


def prepare_hw_resources(sys_platform):
    """
    Converting System platform to resources of SpeedSim style and saving proper data.

    Currently we are supporting one level of ip -> resources
    TODO: support multiple levels
    :param sys_platform:
    :return: dictionary of name -> resources
    """
    resources = dict()
    for ip in sys_platform.ips:
        for r, _type in [(d, ResourceDesc.DRIVER) for d in ip.drivers] + \
                                [(e, ResourceDesc.EX_U) for e in ip.executing_units]:
            name = ip.name + NAME_SEPARATOR + r.name
            resource = ResourceState(name, 0)
            resource.attach_attribute(RESOURCE, r)
            resource.attach_attribute(TYPE, _type)
            resources[name] = resource
    return resources


def connect_transitions(net, from_name, to_name, put_samples=1, get_samples=1, buf_size=1, init_count=0, gating=AND,
                        places_added=None, arcs_added=None):
    """
    Connects two transitions in the given net
    If OR gating connects all the sources the the same buffer and then to the target

    :param net:
    :param from_name: source name
    :param to_name: target name
    :param put_samples: how many input samples the connection delivers to the buffer
    :param get_samples: how many output samples the connections gets from the buffer
    :param buf_size: buffer size
    :param init_count: starting tokens in the buffer
    :param gating: OR or AND
    :param places_added: a dict that represents the places that has already been added: place_name -> place
    :param arcs_added: a dict that represents the arcs that has already been added: arc_name -> place
    :return: places_add, arcs_added
    """
    places_added = places_added or dict()
    arcs_added = arcs_added or dict()
    other_arcs_multiplier = 1
    current_arc_multiplier = 1
    if gating == AND:
        place_name = from_name + NAME_SEPARATOR + to_name + "__p"
        place = PnmlModel.Place("b=" + str(buf_size), id=place_name, init_count=init_count, buff_size=buf_size)
        net.add_place(place)
        net.add_arc(PnmlModel.Arc(place.id, to_name,
                                  id="post__" + from_name + NAME_SEPARATOR + to_name,
                                  weight=get_samples, inscription=str(get_samples)))
    elif gating == OR:
        place_name = OR + NAME_SEPARATOR + to_name + "__p"
        to_target_arc_name = "post__" + OR + NAME_SEPARATOR + to_name
        if place_name not in places_added.keys():
            place = PnmlModel.Place("b=" + str(buf_size), id=place_name, init_count=init_count, buff_size=buf_size)
            target_arc = PnmlModel.Arc(place.id, to_name, id=to_target_arc_name, weight=get_samples,
                                       inscription=str(get_samples))
            net.add_arc(target_arc)
            net.add_place(place)
            places_added[place_name] = place
            arcs_added[to_target_arc_name] = target_arc

        # If the place of the OR gating was already created, updates it attributes and the arc to the target attributes
        else:
            place = places_added[place_name]
            to_target_arc = arcs_added[to_target_arc_name]
            old_get_samples = to_target_arc.get_attribute(WEIGHT, 0)
            new_get_samples = lcm(old_get_samples, get_samples)
            other_arcs_multiplier = int(new_get_samples/old_get_samples)
            current_arc_multiplier = int(new_get_samples/get_samples)
            to_target_arc.set_attribute(WEIGHT, new_get_samples)
            to_target_arc.inscription = str(new_get_samples)

            old_buf_size = place.get_attribute(BUFFER_SIZE, 0)
            old_init_count = place.get_attribute(INIT_COUNT, 0)
            new_buf_size = old_buf_size * other_arcs_multiplier + buf_size * current_arc_multiplier
            new_init_count = old_init_count + init_count * current_arc_multiplier
            place.set_attribute(BUFFER_SIZE, new_buf_size)
            place.set_attribute(INIT_COUNT, new_init_count)
            place.marking = "b=" + str(new_buf_size)
    else:
        raise ValueError("The gating attribute of a task need to be AND or OR")

    if other_arcs_multiplier > 1:
        for arc in arcs_added.values():
            if arc.target == place.id:
                old_put_samples = arc.get_attribute(WEIGHT, 0)
                arc.set_attribute(WEIGHT, old_put_samples * other_arcs_multiplier)
                arc.inscription = str(old_put_samples * other_arcs_multiplier)
    from_source_arc = PnmlModel.Arc(from_name, place.id, id="pre__" + from_name + NAME_SEPARATOR + to_name,
                                    weight=put_samples * current_arc_multiplier,
                                    inscription=str(put_samples * current_arc_multiplier))
    net.add_arc(from_source_arc)
    arcs_added[from_source_arc.id] = from_source_arc

    return places_added, arcs_added


def lcm(a, b):
    return a * b // gcd(a, b)


def copy_task(task, split, wltask):
    """
    Creates a copy task with the splitted data and proc cycles

    :param task: the task that needs to be copied
    :param split: the split for the task
    :param wltask: father task name
    :return: Task
    """
    new_task = Task(task.name, task.type)
    new_task.processing_cycles = math.ceil(task.processing_cycles / split)
    new_task.read_bytes = math.ceil(task.read_bytes / split)
    new_task.write_bytes = math.ceil(task.write_bytes / split)
    new_task.attributes = deepcopy(task.attributes)
    new_task.attach_attribute(TASK_SPLIT_COUNT, split)
    if wltask != '':
        new_task.attach_attribute(WLTASK_NAME, wltask)
    return new_task


def connect_task_to_successors(net, task, from_name, wltask_name):
    for suc, con in task.successors.items():
        if suc.type == TYPES.WORKLOAD:
            t_start_trigger = wltask_name + suc.name + NAME_SEPARATOR + TRIGGER_IN
        else:
            t_start_trigger = wltask_name + suc.name
        connect_transitions(net, from_name, t_start_trigger, con, wltask_name)


def prepare_wl_to_sim(workload, mapping, net=None, wltask_name='', split=1):
    """
    Prepare workload to pnml:
        - converting tasks to transitions
        - converting connections to places and arcs

    :return: pnmlModel
    """
    if net is None:
        first_level = True
        net = PnmlModel.Net(transitions=[], places=[], arcs=[])
    else:
        first_level = False
    for task in workload.tasks:
        if task.type == TYPES.START:
            if not first_level:
                continue
            net.add_place(PnmlModel.Place(task.name, id=task.name, type=PnmlModel.Place.Type.START,
                                          iterations=task.get_attribute(TaskMetaData.ITERATIONS, 1),
                                          wait_delay=task.get_attribute(TaskMetaData.WAIT_DELAY, 0),
                                          start_delay=task.get_attribute(TaskMetaData.START_DELAY, 0),
                                          buff_size=task.get_attribute(TaskMetaData.ITERATIONS, 1)))
            start_trigger = task.name + NAME_SEPARATOR + START_TRIGGER
            net.add_transition(PnmlModel.Transition(start_trigger, id=start_trigger, runtime=0))
            net.add_arc(PnmlModel.Arc(task.name, start_trigger, id="post__" + start_trigger, weight=1))
        elif task.type == TYPES.END:
            if not first_level:
                continue
            net.add_place(PnmlModel.Place(task.name, id=task.name, type=PnmlModel.Place.Type.END))
            end_trigger = task.name + NAME_SEPARATOR + END_TRIGGER
            net.add_transition(PnmlModel.Transition(end_trigger, id=end_trigger, runtime=0))
            net.add_arc(PnmlModel.Arc(end_trigger, task.name, id="post__" + end_trigger, weight=1))
        elif task.type == TYPES.WORKLOAD:
            trigger_in = wltask_name + task.name + NAME_SEPARATOR + TRIGGER_IN
            net.add_transition(PnmlModel.Transition(trigger_in, id=trigger_in, runtime=0))
            trigger_out = wltask_name + task.name + NAME_SEPARATOR + TRIGGER_OUT
            net.add_transition(PnmlModel.Transition(trigger_out, id=trigger_out, runtime=0))
            net = prepare_wl_to_sim(task.workload, task.mapping, net,
                                    wltask_name + task.name + NAME_SEPARATOR, task.split)
        else:
            tr = PnmlModel.Transition(wltask_name + task.name, id=wltask_name + task.name,
                                      cycles=task.processing_cycles/split)
            tr.set_attribute(TASK, copy_task(task, split, wltask_name))
            tr.set_attribute(TYPE, task.type)
            task_mapping = mapping.get_task_mapping(task.name)
            if task_mapping is not None:
                tr.set_attribute(MappingDesc.MAPPING, task_mapping)
            net.add_transition(tr)

    for task in workload.tasks:
        if task.type == TYPES.START:
            if first_level:
                start_trigger = wltask_name + task.name + NAME_SEPARATOR + START_TRIGGER
            else:
                start_trigger = wltask_name + TRIGGER_IN
            for suc, con in task.successors.items():
                if suc.type == TYPES.WORKLOAD:
                    t_trigger = wltask_name + suc.name + NAME_SEPARATOR + TRIGGER_IN
                elif suc.type == TYPES.END:
                    t_trigger = wltask_name + suc.name + NAME_SEPARATOR + TRIGGER_OUT
                else:
                    t_trigger = wltask_name + suc.name
                connect_transitions(net, start_trigger, t_trigger, split, split, 1, con.init,
                                    suc.get_attribute(TaskMetaData.GATING, AND))
        elif task.type != TYPES.END:
            if task.type != TYPES.WORKLOAD:
                for suc, con in task.successors.items():
                    if suc.type == TYPES.WORKLOAD:
                        t_trigger = wltask_name + suc.name + NAME_SEPARATOR + TRIGGER_IN
                    elif suc.type == TYPES.END:
                        if wltask_name == '':
                            t_trigger = suc.name + NAME_SEPARATOR + END_TRIGGER
                        else:
                            t_trigger = wltask_name + TRIGGER_OUT
                    else:
                        t_trigger = wltask_name + suc.name
                    connect_transitions(net, wltask_name + task.name, t_trigger, con.put_samples, con.get_samples,
                                        con.buf_size, con.init, suc.get_attribute(TaskMetaData.GATING, AND))
            else:
                end_trigger = wltask_name + task.name + NAME_SEPARATOR + TRIGGER_OUT
                for suc, con in task.successors.items():
                    if suc.type == TYPES.WORKLOAD:
                        t_trigger = wltask_name + suc.name + NAME_SEPARATOR + TRIGGER_IN
                    elif suc.type == TYPES.END:
                        t_trigger = suc.name + NAME_SEPARATOR + END_TRIGGER
                    else:
                        t_trigger = wltask_name + suc.name
                    connect_transitions(net, end_trigger, t_trigger, con.put_samples, con.get_samples,
                                        con.buf_size, con.init, suc.get_attribute(TaskMetaData.GATING, AND))
    if first_level:
        return PnmlModel(nets=[net])
    else:
        return net


def report_usage():
    """
    Reporting usages of SpeedSim to Diamond - supporting both Linux and Windows.

    :return:
    """
    version = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    try:
        if platform.system() == LINUX:
            diamond = "/usr/intel/bin/dts_register"
            subprocess.run([diamond, '-tool', TOOL, '-version', version])
        elif platform.system() == WINDOWS:
            diamond = "\\ger.corp.intel.com\\ec\\proj\\DPGEC\\tmg\\dts\\Tools\\DTS CADRoot Releases\\Diamond\\" \
                      "3.2.2\\3.2.2_vs2015_release_64\\dynamic\\Diamond_CLI\\Diamond_CLI.exe"
            subprocess.run([diamond, '-t=' + TOOL, '-v=' + version])
        else:
            return
    except:  # noqa: E722
        pass


class Logger:
    """
    Debugging capability of SpeedSim by defining SPEEDSIM_DEBUG as environment variable
    """
    class __SpeedSimLogger:
        def __init__(self):
            if SPEEDSIM_DEBUG in os.environ:
                logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(message)s')
                self.logger = logging.getLogger()
            else:
                self.logger = None

        def log(self, time, msg):
            if not self.logger:
                return
            self.logger.debug('DEBUG: ' + time + 'us :: ' + msg)

    instance = None

    def __init__(self):
        if not Logger.instance:
            Logger.instance = Logger.__SpeedSimLogger()

    @staticmethod
    def log(time, msg):
        if not Logger.instance:
            return
        Logger.instance.log(str(time), msg)


Logger()
