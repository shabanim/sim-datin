from .multidispatch import multimethod
from .network import Pod
from .collective import AllReduce
import math
from .constants import Constants

@multimethod(Pod, AllReduce)
def comms_scaleout(pod: Pod, allreduce: AllReduce, message_size):
    latency_time_us = 2*pod["so_total_lat_us"] * pod["so_steps"]
    tiles_per_nic = pod["so_tiles_per_host"] / pod["so_nics"]
    PVC_within_pod = pod["pvc_inside_pod"]
    node_within_pod = int(PVC_within_pod/pod["num_PVC_per_host"])
    num_of_pods = int(pod["num_pvc"]/PVC_within_pod)
    latency_time_us_pod = 2*pod["so_total_lat_us"]* math.log(node_within_pod, 2)
    latency_time_us_accross_pod = 2 * pod["so_total_lat_us"] * math.log(num_of_pods, 2)
    message_size = message_size / Constants.GIGACONV

    if message_size != 0:
        if pod["so_hw_type"] == 7: # pod.py
            if pod["so_data_parallel_with_model_split"] == 1: # mp wt_grad allreduce
                # print(pod["so_data_parallel_with_model_split"])
                # print(pod["so_host"])
                dp_inside_pod = node_within_pod / math.ceil((pod["model_split"] / pod["so_tiles_per_host"]))
                # print("dp_inside_pod:",dp_inside_pod)
                # print("num_of_pods:", num_of_pods)
                bw_time_us_1 = 2 * (dp_inside_pod - 1) / dp_inside_pod * message_size / \
                               (pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                bw_time_us_2 = 2 * (num_of_pods - 1) / num_of_pods * tiles_per_nic * (message_size / dp_inside_pod) / \
                               (pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                #bw_time_us = bw_time_us_1 + bw_time_us_2


            elif pod["so_data_parallel_with_model_split"] == 2:  # dp wt_grad allreduce
                if pod["hybrid_model"]:
                    # new logic
                    # For 128 split
                    nodes_working_within_pods = pod["model_split"]/pod["so_tiles_per_host"]

                    #so_tiles_per_host = pvc per host * tiles per PVC
                    # 64/16 = 4
                    bw_time_us_1 = 2 * (nodes_working_within_pods - 1)/ nodes_working_within_pods * (
                            message_size / pod["so_tiles_per_host"]) / (
                                        pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                    #bw_time_us_2 = 2*(num_of_pods-1)/(num_of_pods)*tiles_per_nic * (message_size/(pod["so_tiles_per_host"]*nodes_working_within_pods))/(pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                else:
                    # print(pod["so_data_parallel_with_model_split"])
                    # print("9999")
                    bw_time_us_1 = 2 * (node_within_pod - 1) / node_within_pod  * (
                            message_size / pod["so_tiles_per_host"]) / (
                                        pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                    bw_time_us_2 = 2 * (num_of_pods - 1) / num_of_pods * tiles_per_nic * (
                            message_size / (pod["so_tiles_per_host"]*node_within_pod)) / (
                                        pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                #bw_time_us = bw_time_us_1+bw_time_us_2

            elif pod["so_data_parallel_with_model_split"] == 3: # reduce
                # print(pod["so_data_parallel_with_model_split"])
                # print(pod["so_host"])
                # print("mp:",pod["model_split"])
                dp_inside_pod = node_within_pod / math.ceil((pod["model_split"] / pod["so_tiles_per_host"]))
                dp_inside_node = math.ceil((pod["so_tiles_per_host"] / pod["model_split"]))
                # print("dp_inside_pod:",dp_inside_pod)
                # print("message_size:",message_size)
                bw_time_us_1 = 2 * (dp_inside_pod - 1) / dp_inside_pod* (message_size/dp_inside_node) / \
                             (pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                #print("bw_time_us_1:",bw_time_us_1)
                # print("num_of_pods:",num_of_pods)
                bw_time_us_2 = 2 * (num_of_pods - 1) / num_of_pods * tiles_per_nic * (message_size/(dp_inside_node*dp_inside_pod)) / \
                             (pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                #print("bw_time_us_2:", bw_time_us_2)
                #bw_time_us = bw_time_us_1 + bw_time_us_2

            elif pod["so_data_parallel_with_model_split"] == 4:  # a2a Scaleout
                if pod["hybrid_model"]:
                    # new logic
                    # For 128 split
                    nodes_working_within_pods = pod["model_split"]/pod["so_tiles_per_host"]

                    #so_tiles_per_host = pvc per host * tiles per PVC
                    # 64/16 = 4
                    #bw_time_us_1 within pod
                    #""        _2 across pod
                    bw_time_us_1 = (nodes_working_within_pods - 1)/ nodes_working_within_pods * (message_size) / (
                                        pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                    bw_time_us_2 = ((num_of_pods-1)/(num_of_pods)*message_size*tiles_per_nic)/(
                                        pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                else:
                    bw_time_us_1=0
                    bw_time_us_2=0
                #bw_time_us = bw_time_us_1+bw_time_us_2
            else: # mp fwd, inp_grad allreduce
                # print(node_within_pod)
                # print(pod["so_host"])
                if pod["so_host"] <= node_within_pod :
                    bw_time_us_1 = 2 * (pod["so_host"] - 1) / pod["so_host"] * \
                                 (message_size / pod["so_tiles_per_host"]) / pod["total_Xe_bw_GBps"] * Constants.sec_2_us
                    bw_time_us_2 = 0
                else:
                    bw_time_us_1 = (node_within_pod - 1) / node_within_pod * (message_size/pod["so_tiles_per_host"]) / (
                        pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
                    numAccrossPod = pod["so_host"]/node_within_pod
                    bw_time_us_2 = ((numAccrossPod - 1) / (numAccrossPod) * message_size/(node_within_pod*pod["so_tiles_per_host"]) * tiles_per_nic) / (
                            pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
                    #bw_time_us = bw_time_us_1 + bw_time_us_2



        Gamma_term_us = 0
        total_time_us1 = bw_time_us_1 +  Gamma_term_us + (latency_time_us_pod if bw_time_us_1 > 0 else 0)
        total_time_us2 = bw_time_us_2 +  Gamma_term_us + (latency_time_us_accross_pod if bw_time_us_2 > 0 else 0)

    else:
        total_time_us1 = 0
        total_time_us2 = 0

    return total_time_us1,total_time_us2
    
    
#glueless
# @multimethod(Pod, AllReduce)
# def comms_scaleout(pod: Pod, allreduce: AllReduce, message_size):
#     tiles_per_nic = pod["so_tiles_per_host"] / pod["so_nics"]
#     PVC_within_pod = 64
#     node_within_pod = int(PVC_within_pod/pod["num_PVC_per_host"])
#     num_of_pods = int(pod["num_pvc"]/PVC_within_pod)
#     message_size = message_size / Constants.GIGACONV
#     latency_time_us = pod["so_host_involvement"] + 2 * (pod["so_latency"]* (node_within_pod*pod["num_tiles_per_pvc"] - 1))
#     print("message_size:",message_size)
#     print("latency_time_us:",latency_time_us)
#     print("hi:",pod["so_data_parallel_with_model_split"])
#     if message_size != 0:
#         if pod["so_hw_type"] == 7: # pod.py
#             if pod["so_data_parallel_with_model_split"] == 2:  # dp wt_grad allreduce
#                 print("glueless")
#                 print(pod["num_tiles_per_pvc"])
#                 if pod["hybrid_model"]:
#                     # new logic
#                     # For 128 split
#                     nodes_working_within_pods = pod["model_split"]/pod["so_tiles_per_host"]
#
#                     #so_tiles_per_host = pvc per host * tiles per PVC
#                     # 64/16 = 4
#                     bw_time_us_1 = 2 * (nodes_working_within_pods - 1)/ nodes_working_within_pods * (
#                             message_size / pod["so_tiles_per_host"]) / (
#                                         pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
#                     bw_time_us_2 = 2*(num_of_pods-1)/(num_of_pods)*tiles_per_nic * (message_size/(pod["so_tiles_per_host"]*nodes_working_within_pods))/(pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
#                 else:
#                     bw_time_us_1 = 2 * (node_within_pod*pod["num_tiles_per_pvc"] - 1) / (node_within_pod*pod["num_tiles_per_pvc"])  * (
#                             message_size / pod["so_tiles_per_host"]) / (
#                                         pod["total_Xe_bw_GBps"]) * Constants.sec_2_us
#                     print("bw_time_us_1:",bw_time_us_1)
#                     bw_time_us_2 = 2 * (num_of_pods - 1) / num_of_pods * tiles_per_nic * (
#                             message_size / (pod["so_tiles_per_host"]*node_within_pod)) / (
#                                         pod["so_total_inter_host_bw_gbps"] / pod["so_nics"]) * Constants.sec_2_us
#                     print("bw_time_us_2:", bw_time_us_2)
#                 bw_time_us = bw_time_us_1+bw_time_us_2
#
#             else: # mp fwd, inp_grad allreduce
#                 bw_time_us = 2 * (pod["so_host"]*pod["num_tiles_per_pvc"] - 1) / (pod["so_host"]*pod["num_tiles_per_pvc"]) * \
#                                                      (message_size / pod["so_tiles_per_host"]) / pod["total_Xe_bw_GBps"] * Constants.sec_2_us
#         Gamma_term_us = 0
#         total_time_us = latency_time_us + bw_time_us + Gamma_term_us
#         print("total_time_us:",total_time_us)
#     else:
#         total_time_us = 0
#
#     return total_time_us
