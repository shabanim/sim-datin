from .multidispatch import multimethod
from .network import FatTree
from .collective import AllReduce, Reduce, All2All, AllGather
import math


def build_fattree(network):
    # 1/2/3 fat tree --------------------
    no_of_ports_in_switch = network["so_ports_switch"]
    no_of_GPUs = network["num_pvc"]
    no_of_nics_per_node = network["so_nics"]
    max_number_of_GPU_supported_1_tier = no_of_ports_in_switch
    max_number_of_GPU_supported_2_tier = no_of_ports_in_switch * no_of_ports_in_switch / 2
    max_number_of_GPU_supported_3_tier = no_of_ports_in_switch * no_of_ports_in_switch * no_of_ports_in_switch / 2
    if no_of_GPUs <= max_number_of_GPU_supported_1_tier:
        latency_time_us = 2 * network["so_total_lat_us"] * network["so_steps"]
        no_of_leafswitch = 1
        no_of_spineswitch = 0
        no_of_coreswitch = 0
    elif no_of_GPUs <= max_number_of_GPU_supported_2_tier:
        latency_time_us = 2 * 2 * network["so_total_lat_us"] * network["so_steps"]
        if (no_of_GPUs / (no_of_ports_in_switch / 2)) % 2 == 0:
            no_of_leafswitch = (no_of_GPUs / (no_of_ports_in_switch / 2))
            no_of_spineswitch = no_of_leafswitch / 2
        else:
            no_of_leafswitch = 2 ** (math.ceil(math.log(no_of_GPUs / (no_of_ports_in_switch / 2), 2)))
            no_of_spineswitch = 2 ** (math.ceil(math.log(no_of_leafswitch / 2, 2)))
        no_of_coreswitch = 0
    elif no_of_GPUs <= max_number_of_GPU_supported_3_tier:
        latency_time_us = 3 * 2 * network["so_total_lat_us"] * network["so_steps"]
        no_of_host = 140
        no_of_SU = no_of_host / (no_of_ports_in_switch / 2)
        no_of_leafswitch = no_of_GPUs / (no_of_ports_in_switch / 2)
        no_of_leafswitch_per_SU = no_of_leafswitch / no_of_SU
        no_of_spinegroup = no_of_leafswitch_per_SU
        no_of_leafswitch_down_port = (no_of_ports_in_switch / 2)
        no_of_spine_switch_per_group = no_of_leafswitch_down_port / math.floor(no_of_leafswitch_down_port /
                                                                               no_of_leafswitch_per_SU)
        no_of_spineswitch = no_of_spine_switch_per_group * no_of_spinegroup
        no_of_coreswitch = no_of_leafswitch / 2
    else:
        raise Exception("Fat tree Not supported for this config, change switch configurations!!")


    return latency_time_us


@multimethod(FatTree, Reduce)
def comms_scaleout(fattree: FatTree, reduce: Reduce, message_size):
    pass

@multimethod(FatTree, All2All)
def comms_scaleout(fattree: FatTree, a2a: All2All, message_size):
    pass

@multimethod(FatTree, AllGather)
def comms_scaleout(fattree: FatTree, allgather: AllGather, message_size):
    pass

@multimethod(FatTree, AllReduce)
def comms_scaleout(fattree: FatTree, allreduce: AllReduce, message_size):
    latency_time_us = build_fattree(fattree)
    tiles_per_nic = fattree["so_tiles_per_host"] / fattree["so_nics"]


    if message_size != 0:
        # TODO: refactor below
        # 1 and 3 are same
        # 2 and else are same

        if fattree["so_hw_type"] == 1:  # fattree
            if fattree["so_data_parallel_with_model_split"] == 1:  # mp wt_grad allreduce
                bw_time_us = 2 * (fattree["so_host"] - 1) / fattree["so_host"] * tiles_per_nic * message_size \
                             / (fattree["so_total_inter_host_bw_gbps"] / fattree["so_nics"]) * 0.001
            elif fattree["so_data_parallel_with_model_split"] == 2:  # dp wt_grad allreduce
                bw_time_us = 2 * (fattree["so_host"] - 1) / fattree["so_host"] * tiles_per_nic * (
                        message_size / fattree["so_tiles_per_host"]) / (
                                     fattree["so_total_inter_host_bw_gbps"] / fattree["so_nics"]) * 0.001
            elif fattree["so_data_parallel_with_model_split"] == 3:  # reduce
                dp = (fattree["num_pvc"] / fattree['num_PVC_per_host']) / math.ceil(
                    fattree["model_split"] / fattree['so_tiles_per_host'])
                # print("DP:",dp)
                bw_time_us = 2 * (dp - 1) / dp * tiles_per_nic * message_size / \
                             (fattree["so_total_inter_host_bw_gbps"] / fattree["so_nics"]) * 0.001
            elif fattree["so_data_parallel_with_model_split"] == 4:  # a2a Scaleout
                bw_time_us = tiles_per_nic * (message_size * (fattree["so_host"] - 1) / fattree["so_host"]) / \
                             (fattree["so_total_inter_host_bw_gbps"] / fattree["so_nics"]) * 0.001
            else: # mp fwd, inp_grad allreduce
                bw_time_us = 2 * (fattree["so_host"] - 1) / fattree["so_host"] * tiles_per_nic * (
                        message_size / fattree["so_tiles_per_host"]) / (
                                     fattree["so_total_inter_host_bw_gbps"] / fattree["so_nics"]) * 0.001

        Gamma_term_us = 0
        total_time_us = latency_time_us + bw_time_us + Gamma_term_us


    else:
        total_time_us = 0

    return total_time_us
