from ring import comms
import yaml

from knobs import Knobs
from network import Ring, FatTree, P2P, Switch, BidirRing, Hypercube
from collective import AllReduce, All2All, AllGather, ReduceScatter

###################################################################################
# Check Behavior
###################################################################################



if __name__ == '__main__':
    config_file = "../../modelzoo/base_param_cfg.yml"
    knobs = Knobs(config_file=config_file)

    # dummy values
    message_size = 100
    tiles_per_socket = 2
    sockets = 8
    for n in [P2P(knobs.network_knobs), Ring(knobs.network_knobs), Switch(knobs.network_knobs),
              FatTree(knobs.network_knobs), BidirRing(knobs.network_knobs)]:
        for c in [AllReduce(knobs.collective_knobs), ReduceScatter(knobs.collective_knobs), AllGather(knobs.collective_knobs),
                  All2All(knobs.collective_knobs)]:
            stats = comms(n, c, message_size, tiles_per_socket, sockets)
            if stats:
                print(stats.su_time_us, stats.mdfi_achieved_BW)
            try:
                comms(n, c, message_size, tiles_per_socket, sockets)
            except TypeError:
                nt = type(n).__class__.__bases__
                ct = type(c).__class__.__bases__
                print("Type error {} {}".format(nt[0].__name__, ct[0].__name__))