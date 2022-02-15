import math
import json
import numpy as np
from .constants import Constants

class COLUMNS:
    """
    class containing string constants used as column names for various metric and intermediate results stored as CSV
    """
    msg_size = "Msg_size"
    algo = "algo"
    no_of_gpu = "No_of_GPU"
    no_of_tile = "No_of_tile_per_socket"
    pass_type = "MSG_PASS_Type"
    layer_id = "layer_ID"
    fwd_time = "Fwd time"
    bwd_time = "Bwd time"
    wt_time = "Wt grad time"



def _get_xe_link_BW_for_switch_scaleout(config):
    fabric_efficiency = config["su_link_eff"] * config["su_packet_size"] / (
        config["su_packet_size"] + config["su_msg_header"] + config["su_packet_resp"])
    serdes_lane = config["serdes_lane"]
    scale_up_BW_per_link_PEAK = config["serdes_rate_gbps"] * serdes_lane / Constants.BYTE
    if config["so_BW_per_link_ACHIEVABLE_overwrite"]:
        scale_out_BW_per_link_ACHIEVABLE = config["so_BW_per_link_ACHIEVABLE_value"]
    else:
        scale_out_BW_per_link_ACHIEVABLE = scale_up_BW_per_link_PEAK * fabric_efficiency
    total_scale_out_BW = scale_out_BW_per_link_ACHIEVABLE *config["links_scaleout"] #config["links"] #
    return total_scale_out_BW


def add_checkpoint_info_into_json(workload_graph,start_number,interval):
    with open(workload_graph) as fin:
        netinfo = json.load(fin)
    cpt_number=0
    count=0
    for i in netinfo['nodes']:
        if i['data']['Layer']['l_pass']=='fwd':
            if i['data']['Layer']['Layer Index'] < start_number:
                i['data']['Layer']['Checkpoint_number'] ="nan"
            else:
                count=count+1
                i['data']['Layer']['Checkpoint_number'] = cpt_number
                if count==interval:
                    count=0
                    cpt_number=cpt_number+1
                    # print(i['data']['Layer']['Layer Index'])
        else:
            i['data']['Layer']['Checkpoint_number'] = "nan"
    with open(workload_graph, 'w') as f:
        json.dump(netinfo, f, indent=4)
    return