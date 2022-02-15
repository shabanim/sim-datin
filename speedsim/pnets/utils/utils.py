import copy

from pnets.attributes import (HW_RESOURCE, MEMORY, PROCESSING, READ,
                              READ_PERCENTAGE, RUNTIME, WEIGHT, WRITE)
from pnets.pn_model import PnmlModel

MB_TO_B = 1024*1024


def flat_model_to_rpw(model, data_to_runtime_func, resources):
    """
    Flattening PNML model to read, process and write. where each task is flattered to 3 tasks.
    task1 name is: original task + _read
    task2 name is: original task + _proc
    task3 name is: original task + _write
    each read/write task has a new attribute of data_bytes defines amount of data of it.
    :param model: PNML model to be flattered
    :param data_to_runtime_func: function takes data amount in bytes and return run time in us.
    :param resources: HW dictionary (hw_resource, <op>) -> new hw resource
    for example:
        {(CPU, Read): CPU.DMA0, (CPU, Proc): CPU.Core0}
    :return: new flattered PNML model.
    """
    new_model = PnmlModel()
    for net in model.nets:
        new_net = PnmlModel.Net(id=net.id)
        new_model.nets.append(new_net)
        for transition in net.transitions:
            total = float(transition.get_attribute(MEMORY)) * MB_TO_B
            read = total * (float(transition.get_attribute(READ_PERCENTAGE))/100.0)
            write = total - read
            runtime = transition.get_attribute(RUNTIME)
            hw_resource = transition.get_attribute(HW_RESOURCE)

            # Transitions
            new_net.add_transition(PnmlModel.Transition(transition.marking + "_" + READ,
                                                        id=transition.id + "_" + READ,
                                                        runtime=data_to_runtime_func(read),
                                                        data_bytes=read,
                                                        hw_resource=resources.get((hw_resource, READ), hw_resource),
                                                        type=READ))
            new_net.add_transition(PnmlModel.Transition(transition.marking + "_" + PROCESSING,
                                                        id=transition.id + "_" + PROCESSING,
                                                        runtime=runtime,
                                                        hw_resource=resources.get((hw_resource, PROCESSING),
                                                                                  hw_resource),
                                                        type=PROCESSING))
            new_net.add_transition(PnmlModel.Transition(transition.marking + "_" + WRITE,
                                                        id=transition.id + "_" + WRITE,
                                                        runtime=data_to_runtime_func(write),
                                                        data_bytes=write,
                                                        hw_resource=resources.get((hw_resource, WRITE), hw_resource),
                                                        type=WRITE))
            # Places
            new_net.add_place(PnmlModel.Place(transition.id + "_r_p_p",
                                              id=transition.id + "_r_p_p",
                                              init=0, buff_size=100000))
            new_net.add_place(PnmlModel.Place(transition.id + "_p_w_p",
                                              id=transition.id + "_p_w_p",
                                              init=0, buff_size=100000))

            # Arcs
            new_net.add_arc(PnmlModel.Arc(transition.id + "_" + READ, transition.id + "_r_p_p",
                                          id=transition.id + "_r_p_pre_arc", weight=1))
            new_net.add_arc(PnmlModel.Arc(transition.id + "_r_p_p", transition.id + "_" + PROCESSING,
                                          id=transition.id + "_r_p_post_arc", weight=1))
            new_net.add_arc(PnmlModel.Arc(transition.id + "_" + PROCESSING, transition.id + "_p_w_p",
                                          id=transition.id + "_p_w_pre_arc", weight=1))
            new_net.add_arc(PnmlModel.Arc(transition.id + "_p_w_p", transition.id + "_" + WRITE,
                                          id=transition.id + "_p_w_post_arc", weight=1))

        places_ids = []
        for place in net.places:
            new_net.add_place(copy.deepcopy(place))
            if place.id not in places_ids:
                places_ids.append(place.id)

        for arc in net.arcs:
            new_arc = None
            if arc.src in places_ids:
                new_arc = PnmlModel.Arc(arc.src, arc.target + "_" + READ,
                                        id=None, inscription=arc.inscription,
                                        weight=(arc.get_attribute(WEIGHT) if arc.get_attribute(WEIGHT) is not None
                                                else 1))
            elif arc.target in places_ids:
                new_arc = PnmlModel.Arc(arc.src + "_" + WRITE, arc.target,
                                        id=None, inscription=arc.inscription,
                                        weight=(arc.get_attribute(WEIGHT) if arc.get_attribute(WEIGHT) is not None
                                                else 1))
            if new_arc is not None:
                new_net.add_arc(new_arc)
    return new_model
