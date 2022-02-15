"""
**Utils** - Multiple utilities and help functions
"""
import json
import math
import os
import sys
from collections import defaultdict
from copy import deepcopy

import pnets.attributes as pn_attr
from asap.counters import Counter
from asap.mapping import Mapping
from asap.strings import (MB_TO_B, MIN_CYCLES, NAME_SEPARATOR, NS, S_2_US,
                          SPLIT, US_2_S, MappingDesc, PMMLPreDefinedAtts,
                          TaskMetaData, ALIGN_TO_CLOCK)
from asap.system_platform import Platform
from asap.workload import TYPES, Connection, Task, WlTask, Workload
from pnets.pn_model import PnmlModel


def load_platform(path):
    """
    Loads a json file and creates a platform by it

    :param path: the path to the json file
    :return: Platform
    """
    with open(path) as json_file:
        data = json.load(json_file)
        system = Platform.load(data)
    return system


def create_rpw_workload():
    """
    Creating read -> process -> write task graph with default values

    :return: Workload
    """
    start = Task('start', TYPES.START)
    read = Task('read', TYPES.READ, read_bytes=1024)
    proc = Task('process', TYPES.PROC, processing_cycles=10)
    write = Task('write', TYPES.WRITE, write_bytes=1024)
    end = Task('end', TYPES.END)

    con1 = Connection('con1', start, read)
    con2 = Connection('con2', read, proc)
    con3 = Connection('con3', proc, write)
    con4 = Connection('con4', write, end)

    return Workload('workload', [start, read, proc, write, end], [con1, con2, con3, con4])


def create_rpw_task(task, metadata=None):
    """
    Creates a workload task that contains read -> process -> write, according to task params.

    If task does not have any memory for read then does not create read.
    If task does not have any processing then does create proc task.
    If task does not have any memory for write then does not create write task.

    :param task: main task that we want to create the read -> process -> write out of
    :param metadata: meta data dictionary describes more details on creating rpw tasks
                     property -> value, owner of this function should be aware of metadata sent
    :return: Workload task
    """
    metadata = metadata or dict()

    proc_cycles = task.processing_cycles
    read_bytes = task.read_bytes
    write_bytes = task.write_bytes
    split = metadata.get(SPLIT, 1)
    if split == 1:
        if int(proc_cycles) == 0 and int(read_bytes) == 0 and int(write_bytes) == 0:
            return task
        if int(read_bytes) == 0 and int(proc_cycles) == 0 and int(write_bytes) != 0:
            task.type = TYPES.WRITE
            return task
        if int(read_bytes) == 0 and int(proc_cycles) != 0 and int(write_bytes) == 0:
            task.type = TYPES.PROC
            return task
        if int(read_bytes) != 0 and int(proc_cycles) == 0 and int(write_bytes) == 0:
            task.type = TYPES.READ
            return task

    start = Task('start', TYPES.START)
    end = Task('end', TYPES.END)

    if int(read_bytes) == 0:
        read_task = None
    else:
        read_task = Task('read', TYPES.READ, read_bytes=read_bytes, id=task.get_attribute('id', 0))

    if int(proc_cycles) == 0:
        proc_task = None
    else:
        proc_task = Task('process', TYPES.PROC, processing_cycles=proc_cycles, id=task.get_attribute('id', 0))

    if int(write_bytes) == 0:
        write_task = None
    else:
        write_task = Task('write', TYPES.WRITE, write_bytes=write_bytes, id=task.get_attribute('id', 0))

    wl = Workload(task.name, [start, end])
    if read_task is not None:
        read_task.counters = deepcopy(task.counters)
        wl.add_task(read_task)
        wl.connect_tasks('1', start, read_task)
    if proc_task is not None:
        proc_task.counters = deepcopy(task.counters)
        wl.add_task(proc_task)
        if read_task is not None:
            wl.connect_tasks('2', read_task, proc_task, buf_size=metadata.get('read_proc_buf_size', sys.maxsize))
        else:
            wl.connect_tasks('2', start, proc_task)
    if write_task is not None:
        write_task.counters = deepcopy(task.counters)
        wl.add_task(write_task)
        if proc_task is not None:
            wl.connect_tasks('3', proc_task, write_task, buf_size=metadata.get('proc_write_buf_size', sys.maxsize))
        elif read_task is not None:
            wl.connect_tasks('3', read_task, write_task, buf_size=metadata.get('proc_write_buf_size', sys.maxsize))
        else:
            wl.connect_tasks('3', start, write_task)
        wl.connect_tasks('4', write_task, end)
    else:
        if proc_task is not None:
            wl.connect_tasks('4', proc_task, end)
        else:
            wl.connect_tasks('4', read_task, end)
    hierarchy_mapping = Mapping('hierarchy_mapping', wl)
    wl_task = WlTask(task.name, wl, hierarchy_mapping)
    wl_task.split = split
    wl_task.counters = deepcopy(task.counters)
    return wl_task


def create_comp_rpw_task(task, metadata=None):
    """
    Creates a workload task that contains read -> process -> write

    :param task: task that we want to create the read -> process -> write out of
    :param metadata: meta data dictionary describes more details on creating rpw tasks
                     property -> value, owner of this function should be aware of metadata sent
    :return: Workload task
    """
    metadata = metadata or dict()

    proc_cycles = task.processing_cycles
    read_bytes = task.read_bytes
    write_bytes = task.write_bytes
    start = Task('start', TYPES.START)
    end = Task('end', TYPES.END)
    read_task = Task('read', TYPES.READ, read_bytes=read_bytes, id=task.get_attribute('id', 0))
    proc_task = Task('process', TYPES.PROC, processing_cycles=proc_cycles, id=task.get_attribute('id', 0))
    write_task = Task('write', TYPES.WRITE, write_bytes=write_bytes, id=task.get_attribute('id', 0))
    wl = Workload(task.name, [start, end, read_task, proc_task, write_task])
    wl.connect_tasks('1', start, read_task)
    wl.connect_tasks('2', read_task, proc_task, buf_size=metadata.get('read_proc_buf_size', sys.maxsize))
    wl.connect_tasks('3', proc_task, write_task, buf_size=metadata.get('proc_write_buf_size', sys.maxsize))
    wl.connect_tasks('4', write_task, end)
    hierarchy_mapping = Mapping('hierarchy_mapping', wl)
    wl_task = WlTask(task.name, wl, hierarchy_mapping)
    wl_task.split = metadata.get(SPLIT, 1)
    read_task.attach_attribute(read_task, wl_task.split)
    read_task.counters = deepcopy(task.counters)
    proc_task.attach_attribute(read_task, wl_task.split)
    proc_task.counters = deepcopy(task.counters)
    write_task.attach_attribute(read_task, wl_task.split)
    write_task.counters = deepcopy(task.counters)
    return wl_task


def create_rpw_by_data_chunk(task, metadata=None):
    """
    Creates a workload task that contains read -> process -> write

    :param task: task that we want to create the read -> process -> write out of
    :param metadata: meta data dictionary describes more details on creating rpw tasks property -> value,
                    owner of this function should be aware of metadata sent.
                    Expected here to have chunk_size attribute
    :return: Workload task
    """
    wl_task = create_rpw_task(task, metadata)
    read_bytes = wl_task.workload.get_task('read').read_bytes
    wl_task.split = math.ceil((read_bytes / metadata.get('chunk_size', read_bytes)))
    return wl_task


def create_memory_task(task, memories=None):
    """
    Creates a read-proc-write task that targets the memory according to the user

    when used inside from_pnml_model needs an overlay function
    :param task: task that we want to create the read -> process -> write out of
    :param memories: dict {'memory name':'percent'}
    :return: Workload task
    """
    if memories is None:
        return create_rpw_task(task)
    wl_task = create_rpw_task(task)

    wl_task.workload.get_task('read').attach_attribute(MappingDesc.MEMORY_TARGETS, deepcopy(memories))
    wl_task.workload.get_task('write').attach_attribute(MappingDesc.MEMORY_TARGETS, deepcopy(memories))
    return wl_task


def create_basic_task(task, meta_data=None):
    """
    Creates a basic task according to the given task
    :param task:
    :param meta_data: used to insert customized attributes to the task, passed through from_pnml_model function
    :return: Task
    """
    return task


def get_data_and_cycles(transition, reference_freq=None):
    """
    Returns the data and cycles of the task according to the reference freq and splits the data by the split percent

    :param transition: transition of a task that we want to calculate the data and cycles from
    :param reference_freq: dict (str hw_resource) -> {'resource': <reference_freq>}
    :return: processing_cycles, read_bytes, write_bytes
    """
    data = transition.get_attribute(pn_attr.MEMORY)
    read_bytes = 0
    write_bytes = 0
    read_percent = float(transition.get_attribute(pn_attr.READ_PERCENTAGE, 0) / 100)
    if data is not None:
        data = float(data) * MB_TO_B
        read_bytes = data * read_percent
        write_bytes = data - read_bytes

    cycles = transition.get_attribute(pn_attr.CYCLES)
    if cycles is None:
        proc_cycles = 0
    elif cycles == 0:
        proc_cycles = 0
    else:
        proc_cycles = cycles
    if proc_cycles == 0:
        proc_cycles = MIN_CYCLES if transition.get_attribute(pn_attr.RUNTIME) is None else \
            (transition.get_attribute(pn_attr.RUNTIME) * US_2_S *
             reference_freq.get(str(transition.get_attribute("hw_resource")), 1 / NS))
    # TODO : Saeed & Or please make your decision
    if proc_cycles < MIN_CYCLES:
        proc_cycles = MIN_CYCLES

    return proc_cycles, read_bytes, write_bytes


def fill_task_counters(transition, task):
    """
    Filling task counters according to transition properties

    :param transition:
    :param task:
    :return:
    """
    counters = transition.get_attribute(pn_attr.PMC)
    if counters is None:
        return
    counters_list = list()
    for counter, value in counters.items():
        counters_list.append(Counter(counter, value))
    task.counters = counters_list


def from_pnml_model(pnml_model, workload_name="Workload", reference_freq=None, hw_resources=None, tasks_att_list=None):
    """
    Converting pnml model to Workload.

    If transition has cycles then uses cycles, otherwise, convert runtime according to reference frequency.

    :param pnml_model:
    :param workload_name:
    :param reference_freq: dict (str hw_resource) -> {'resource': <reference_freq>}
    :param hw_resources: Hardware resources converter and descriptor
                         dict (str hw_resource) -> {'resource': (obj hw_resource), 'attributes': {'attributes': 'val'}}
                         Add attributes to tasks. for metadata and usages,
                         converts pnml hw_resource to Platform resource together with proper attributes
    :param tasks_att_list: list of dict that represent the attribute and values of the tasks that we want to activate
                           the task_function on them: [{'attribute': {'values': list('val'),
                           'function_data': {'function': <function>, 'split': 'value', ...}}}]

                           Expected params:
                               - function
    :return: Workload
    """
    if tasks_att_list is None:
        tasks_att_list = dict()
    if reference_freq is None:
        reference_freq = dict()
    tasks = dict()
    connections = list()
    hw_resources_dict = hw_resources if hw_resources is not None else dict()
    workload = Workload(workload_name, attributes=pnml_model.attributes_dict)
    # clocks_alignment: boolean defines if to hack start delays for clock alignments or not.
    # in case start delay equals one of alignments and need to run start first
    clocks_alignment = True if workload.get_attribute('clocks', None) is not None else False
    special_atts_to_first = [ALIGN_TO_CLOCK]
    mapping = Mapping(workload_name + "_mapping", workload)
    i = 0
    for net in pnml_model.nets:
        for transition in net.transitions:
            hw_resource_desc = hw_resources_dict.get(str(transition.get_attribute("hw_resource")), None)
            hw_resource = hw_resource_desc.get('resource', None) if hw_resource_desc is not None else None

            # Checks if the transition needs to be broke down
            task_function = None
            task_function_metadata = None
            break_down = False
            for tasks_att in tasks_att_list:
                for attr, desc in tasks_att.items():
                    if transition.get_attribute(attr) in desc['values']:
                        function_data = desc.get('function_data')
                        if function_data is not None:
                            task_function = function_data.get('function')
                            task_function_metadata = function_data.get('metadata')
                        if task_function is not None:
                            break_down = True

            if not break_down:
                proc_cycles, read_bytes, write_bytes = get_data_and_cycles(transition, reference_freq)
                main_task = Task(transition.id + NAME_SEPARATOR + transition.get_attribute(pn_attr.NAME, ''),
                                 type=TYPES.GEN, read_bytes=read_bytes,
                                 write_bytes=write_bytes, processing_cycles=proc_cycles, id=transition.id)
                pnml_cycles = transition.get_attribute(pn_attr.CYCLES) or 0
                pnml_runtime = transition.get_attribute(pn_attr.RUNTIME) or 0
                main_task.attach_attribute(pn_attr.CYCLES, pnml_cycles)
                main_task.attach_attribute(pn_attr.RUNTIME, pnml_runtime)
                attach_attributes_to_task(main_task, transition, mapping, hw_resource, hw_resource_desc, tasks_att_list)
                fill_task_counters(transition, main_task)
            else:
                proc_cycles, read_bytes, write_bytes = get_data_and_cycles(transition, reference_freq)
                main_task = Task(transition.id + NAME_SEPARATOR + transition.get_attribute(pn_attr.NAME, ''),
                                 type=TYPES.GEN, read_bytes=read_bytes,
                                 write_bytes=write_bytes, processing_cycles=proc_cycles, id=transition.id)
                fill_task_counters(transition, main_task)
                main_task = task_function(main_task, task_function_metadata)
                if main_task.type == TYPES.WORKLOAD:
                    hierarchy_mapping = main_task.mapping
                    map_tasks = True
                    if hierarchy_mapping.mappings:
                        map_tasks = False

                    first_tasks = []
                    for s in main_task.workload.get_start_tasks():
                        for suc in s.successors:
                            first_tasks.append(suc)
                    for task in main_task.workload.tasks:
                        is_first_task = False
                        if task in first_tasks:
                            is_first_task = True
                        attach_attributes_to_task(task, transition, hierarchy_mapping, hw_resource,
                                                  hw_resource_desc, tasks_att_list, map_tasks,
                                                  is_first_task, special_atts_to_first)
                else:
                    attach_attributes_to_task(main_task, transition, mapping, hw_resource,
                                              hw_resource_desc, tasks_att_list, True)
            tasks[transition.id] = main_task

        places_inputs = defaultdict(list)
        places_outputs = defaultdict(list)

        for arc in net.arcs:
            src, target = arc.src, arc.target
            if tasks.get(target, None) is not None:
                places_outputs[src].append((target, arc.get_attribute(pn_attr.WEIGHT)))
            else:
                places_inputs[target].append((src, arc.get_attribute(pn_attr.WEIGHT)))

        for place in net.places:
            if place.type == PnmlModel.Place.Type.START:
                task = Task(place.id + NAME_SEPARATOR + "START", TYPES.START)
                freq = place.get_attribute(pn_attr.FREQUENCY, None)
                if freq is not None and float(freq) != 0.0:
                    wait_delay = (1.0/float(freq)) * S_2_US
                    task.attach_attribute(TaskMetaData.WAIT_DELAY, wait_delay)
                task.attach_attribute(TaskMetaData.START_DELAY, place.get_attribute(pn_attr.START_DELAY, 0))
                tasks[place.id] = task
                for out, weight in places_outputs[place.id]:
                    connections.append(Connection("con{}".format(i), tasks[place.id], tasks[out]))
                    i += 1
            elif place.type == PnmlModel.Place.Type.END:
                task = Task(place.id + NAME_SEPARATOR + "END", TYPES.END)
                tasks[place.id] = task
                for inp, weight in places_inputs[place.id]:
                    connections.append(Connection("con{}".format(i), tasks[inp], tasks[place.id]))
                    i += 1
            else:
                for inp, in_weight in places_inputs[place.id]:
                    for out, out_weight in places_outputs[place.id]:
                        connections.append(Connection("con{}".format(i), tasks[inp], tasks[out],
                                                      init=place.get_attribute(pn_attr.INIT_COUNT, 0),
                                                      put_samples=in_weight, get_samples=out_weight,
                                                      buf_size=place.get_attribute(pn_attr.BUFFER_SIZE)))
                        i += 1
    workload.tasks = list(tasks.values())
    workload.connections = connections

    if clocks_alignment:
        offsets = [clock.get('offset') for clock in workload.attributes.get('clocks', list())]
        for s in workload.get_start_tasks():
            if int(s.get_attribute(TaskMetaData.START_DELAY, None)) in offsets:
                s.attach_attribute(TaskMetaData.START_DELAY, s.get_attribute(TaskMetaData.START_DELAY) - 0.0001)

    return workload, mapping


def from_pnml_file(pnml_file_path, workload_name="Workload", reference_freq=None, hw_resources=None, tasks_att=None):
    """
    Converting pnml to workload, Basically calls from_pnml_model

    :param pnml_file_path: path to pnml file
    :param workload_name:
    :param reference_freq:
    :param hw_resources:
    :param tasks_att:
    :return: workload
    """
    if not os.path.exists(pnml_file_path) or not os.path.isfile(pnml_file_path):
        raise ValueError("Pnml file was not uploaded correctly!")

    fd = open(pnml_file_path, 'r')
    pnml_model = PnmlModel.read(fd)
    fd.close()
    return from_pnml_model(pnml_model, workload_name, reference_freq, hw_resources, tasks_att)


def attach_attributes_to_task(task, transition, mapping, hw_resource, hw_resource_desc, tasks_att_list, map_tasks=True,
                              is_first_task=True, special_atts_to_first=None):
    """
    Attaching attributes to the tasks according to the attribute dictionary

    :param task:
    :param transition:
    :param mapping: Mapping of the task
    :param hw_resource: hw_resource to map to
    :param hw_resource_desc: the attribute part of the hw_resource_dict
    :param tasks_att_list: the attribute part of the tasks_att
    :param map_tasks: boolean that indicates whether to map tasks according the hw resource
    :param is_first_task: indicates weather this task is first task of workload task or not
    :param special_atts_to_first: special parent attributes need to be moved to first internal tasks only
    :return:
    """
    special_atts_to_first = special_atts_to_first or list()
    if hw_resource is not None and task.type != (TYPES.START or TYPES.END):
        if map_tasks:
            mapping.map_task(task, hw_resource)
        atts = hw_resource_desc.get('attributes', None)
        if atts is not None:
            for att, val in atts.items():
                task.attach_attribute(att, val)
    for att, val in transition.attributes_dict.items():
        if att not in PMMLPreDefinedAtts and att not in special_atts_to_first:
            task.attach_attribute(att, val)
        if is_first_task and att in special_atts_to_first:
            task.attach_attribute(att, val)
    for tasks_att in tasks_att_list:
        for matching_attribute, desc in tasks_att.items():
            if transition.get_attribute(matching_attribute) in desc['values']:
                for attribute in desc.keys():
                    if attribute != 'function_data' and attribute != SPLIT and attribute != 'values':
                        task.attach_attribute(attribute, desc[attribute])
