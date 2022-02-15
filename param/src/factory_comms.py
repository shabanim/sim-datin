from .network import Ring, P2P, BidirRing, Hypercube, Flat, Torus3d, Pod, FatTree
from .collective import AllReduce, AllGather, All2All
from .collective import ReduceScatter, Gather, Scatter, Broadcast
from .collective import Reduce


def get_network_collective(knobs, network_type, collective_type):
    #TODO: move cleanup code to knobs
    collective_type = collective_type.strip()
    network_type = network_type.strip()
    if network_type == "ring":
        network = Ring(knobs=knobs.network_knobs)
    elif network_type == "p2p":
        network = P2P(knobs=knobs.network_knobs)
    elif network_type == "hypercube":
        network = Hypercube(knobs=knobs.network_knobs)
    elif network_type == "bidirring":
        network = BidirRing(knobs=knobs.network_knobs)
    elif network_type == "flat":
        network = Flat(knobs=knobs.network_knobs)
    elif network_type == "torus3d":
        network = Torus3d(knobs=knobs.network_knobs)
    elif network_type == "pod":
        network = Pod(knobs=knobs.network_knobs)
    elif network_type == "fat_tree":
        network = FatTree(knobs=knobs.network_knobs)
    else:
        raise ("Not implmented network type {}"
               .format(network_type))

    if collective_type == "allreduce":
        collective = AllReduce(knobs=knobs.collective_knobs)
    elif collective_type == "gather":
        collective = Gather(knobs=knobs.collective_knobs)
    elif collective_type == "allgather":
        collective = AllGather(knobs=knobs.collective_knobs)
    elif collective_type == "a2a":
        collective = All2All(knobs=knobs.collective_knobs)
    elif collective_type == "reduce_scatter":
        collective = ReduceScatter(knobs=knobs.collective_knobs)
    elif collective_type == "scatter":
        collective = Scatter(knobs=knobs.collective_knobs)
    elif collective_type == "reduce":
        collective = Reduce(knobs=knobs.collective_knobs)
    elif collective_type == "broadcast":
        collective = Broadcast(knobs=knobs.collective_knobs)
    else:
        raise Exception("Not implmented collective type {}"
                        .format(collective_type))

    return network, collective
