from .multidispatch import multimethod
from .network import Flat
from .collective import AllReduce, Reduce, All2All, AllGather
import math
from .constants import Constants

@multimethod(Flat, Reduce)
def comms_scaleout(flat: Flat, reduce: Reduce, message_size):
    pass

@multimethod(Flat, All2All)
def comms_scaleout(flat: Flat, a2a: All2All, message_size):
    pass

@multimethod(Flat, AllGather)
def comms_scaleout(flat: Flat, allgather: AllGather, message_size):
    pass

@multimethod(Flat, AllReduce)
def comms_scaleout(flat: Flat, allreduce: AllReduce, message_size):
    #print(flat["so_steps"])
    latency_time_us = 2 * flat["so_total_lat_us"] * flat["so_steps"]
    tiles_per_nic = flat["so_tiles_per_host"] / flat["so_nics"]

    if message_size != 0:
        # TODO: refactor below
        # 1 and 3 are same
        # 2 and else are same

        if flat["so_hw_type"] == 1:  # flat
            if flat["so_data_parallel_with_model_split"] == 1:  # mp wt_grad allreduce
                bw_time_us = 2 * (flat["so_host"] - 1) / flat["so_host"] * tiles_per_nic * message_size \
                             / (flat["so_total_inter_host_bw_gbps"] / flat["so_nics"]) * 0.001
            elif flat["so_data_parallel_with_model_split"] == 2:  # dp wt_grad allreduce
                bw_time_us = 2 * (flat["so_host"] - 1) / flat["so_host"] * tiles_per_nic * (
                        message_size / flat["so_tiles_per_host"]) / (
                                     flat["so_total_inter_host_bw_gbps"] / flat["so_nics"]) * 0.001
            elif flat["so_data_parallel_with_model_split"] == 3:  # reduce
                dp = (flat["num_pvc"]/flat['num_PVC_per_host'])/math.ceil(flat["model_split"]/flat['so_tiles_per_host'])
                #print("DP:",dp)
                bw_time_us = 2 * (dp - 1) / dp * tiles_per_nic * message_size / \
                             (flat["so_total_inter_host_bw_gbps"] / flat["so_nics"]) * 0.001
            elif flat["so_data_parallel_with_model_split"] == 4:  # a2a Scaleout
                bw_time_us = tiles_per_nic * (message_size * (flat["so_host"] - 1) / flat["so_host"]) / \
                             (flat["so_total_inter_host_bw_gbps"] / flat["so_nics"]) * 0.001
            else: # mp fwd, inp_grad allreduce
                bw_time_us = 2 * (flat["so_host"] - 1) / flat["so_host"] * tiles_per_nic * (
                        (message_size/Constants.GIGACONV) / flat["so_tiles_per_host"]) / (
                                     flat["so_total_inter_host_bw_gbps"] / flat["so_nics"]) * Constants.sec_2_us

        Gamma_term_us = 0
        total_time_us = latency_time_us + bw_time_us + Gamma_term_us


    else:
        total_time_us = 0

    return 0,total_time_us
