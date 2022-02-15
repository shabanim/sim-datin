from copy import deepcopy
from functools import cmp_to_key

import pandas

from . import attributes as PnAttr
from .simulation import (NAN, SIM_EVENT_DURATION, SIM_EVENT_FINISH,
                         SIM_EVENT_RESOURCE, SIM_EVENT_START,
                         SIM_EVENT_TRANSITION, Simulator)


class FeatureDesc:
    """
    Feature description.
    Each feature is essentially a task graph with associated resources.
    Each top-level task is then mapped to a feature so that the actual runtime of a task is determined by
    simulating a feature.
    """
    def __init__(self, pn_model, resources):
        self.pn_model = pn_model
        self.resources = resources


def simulate_feature_graph(top_pnml, top_resources, feature_map, duration=1000000):
    """
    Simulate a PN model using feature simulation
    :param top_pnml: PnmlModel
    :param top_resources: dict {resource_name -> resource_count}
    :param feature_map: dict {feature_name -> feature_desc}
    :param duration: maximum simulation runtime (usec)
    :return: simulation results (pandas dataframe)
    """

    # collect per-feature runtime
    runtime_map = {}
    sim_results = {}
    for feature, desc in feature_map.items():
        sim = Simulator(desc.pn_model, desc.resources)
        sim_results[feature] = sim.run(2 * sum([t.get_attribute(PnAttr.RUNTIME)
                                                for net in desc.pn_model.nets for t in net.transitions]))
        runtime_map[feature] = sim_results[feature][SIM_EVENT_FINISH].max()

    # replace top-level model runtime per with per-faeture runtime:
    pn_model = deepcopy(top_pnml)
    feature_map = {}
    for net in pn_model.nets:
        for tran in net.transitions:
            feature = tran.get_attribute(PnAttr.FEATURE)
            if feature is None:
                # must have pre-defined runtime
                runtime = tran.get_attribute(PnAttr.RUNTIME)
                if runtime is None or runtime < 0:
                    raise(Exception('No feature specified / no runtime specified for transition ' + str(tran.id)))
            else:
                if feature not in runtime_map:
                    raise(Exception("Unknown feature " + str(feature) + " for transition " + str(tran.id)))
                tran.set_attribute(PnAttr.RUNTIME, runtime_map[feature])
                feature_map[tran.id] = feature

    # perform top-level simulation
    sim = Simulator(pn_model, top_resources)
    top_results = sim.run(duration)

    # merge top-level result with per-feature simulation results
    concat = [top_results]
    for tran, feature in feature_map.items():
        tran_starts = top_results[(top_results[SIM_EVENT_TRANSITION] == tran)]
        for i in range(tran_starts.shape[0]):
            start = tran_starts[SIM_EVENT_START].iloc[i]
            resource = tran_starts[SIM_EVENT_RESOURCE].iloc[i]

            detailed = sim_results[feature].copy()
            detailed[SIM_EVENT_START] += start
            detailed[SIM_EVENT_FINISH] += start
            detailed[SIM_EVENT_RESOURCE] = (resource + '.') + detailed[SIM_EVENT_RESOURCE]
            detailed[SIM_EVENT_TRANSITION] = (tran + '.') + detailed[SIM_EVENT_TRANSITION]
            # FIXME: need to accommodate 2 resource indexes (feature resource and resource)
            concat.append(detailed)

    top_results = pandas.concat(concat)

    top_results.loc[top_results.FINISH > duration, [SIM_EVENT_FINISH, SIM_EVENT_DURATION]] = NAN

    sort_tuples = zip(range(top_results.shape[0]), top_results[SIM_EVENT_START].values,
                      top_results[SIM_EVENT_FINISH].values)

    # sort values by START, then by type FINISH, then by resource (sub-feature)
    # if FINISH is NaN keep pushing it to the end
    def _compare(a, b):
        if a[1] < b[1]:
            return -1
        elif a[1] > b[1]:
            return 1
        # a[1] == b[1]
        if a[2] == NAN:
            return 1
        elif b[2] == NAN:
            return -1
        if a[2] < b[2]:
            return -1
        else:
            return 1

    # sorted index
    sort_index = [t[0] for t in sorted(sort_tuples, key=cmp_to_key(_compare))]
    return top_results.iloc[sort_index].reset_index(drop=True)
