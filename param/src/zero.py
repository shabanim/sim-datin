import math
import json
import numpy as np
from .constants import Constants

def zero(knobs, workload_graph, layer_ID_list, msg_size_list, algo_list, msg_pass_type_list):
    model_split = knobs['model_split'] if not knobs['data_parallel'] else 1
    total_tiles = int(knobs["num_pvc"]) * int(knobs["num_tiles_per_pvc"])
    data_parallel_zero = _get_dataparallel_for_zero(total_tiles, model_split)
    print(knobs['ZeRO_type'])
    if knobs['Enable_ZeRO']:
        print("Data_parallel_Zero:", data_parallel_zero)
        if knobs['ZeRO_type'] == 1:
            msg_size_list, algo_list, msg_pass_type_list = _update_comms_zero1(workload_graph, layer_ID_list,
                                                                               msg_size_list,
                                                                               algo_list, msg_pass_type_list,
                                                                               data_parallel_zero)

        elif knobs['ZeRO_type'] == 2:
            zero2_list, total_parameter = _get_LayerID_for_zero_stage2(workload_graph, data_parallel_zero)

            msg_size_list, algo_list, msg_pass_type_list = _update_comms_zero2(zero2_list, total_parameter,
                                                                               layer_ID_list, msg_size_list, algo_list,
                                                                               msg_pass_type_list, data_parallel_zero)
        elif knobs['ZeRO_type'] == 4:
            zeroinf_list, total_parameter = _get_LayerID_for_zero_inf(workload_graph, data_parallel_zero)

            msg_size_list, algo_list, msg_pass_type_list = _update_comms_zero_inf(zeroinf_list, total_parameter,
                                                                               layer_ID_list, msg_size_list, algo_list,
                                                                               msg_pass_type_list, data_parallel_zero)

        update_json_according_to_zero(workload_graph, layer_ID_list, msg_size_list, algo_list, msg_pass_type_list,total_parameter)
    return msg_size_list, algo_list, msg_pass_type_list

def update_json_according_to_zero(json_file,layer_ID_list,msg_size_list,algo_list,msg_pass_type_list,total_parameter):
    with open(json_file) as fin:
        netinfo = json.load(fin)
    temp=np.unique(np.array(layer_ID_list))
    list_of_floats = [float(item) for item in temp]
    unique_layerID = (np.sort(list_of_floats))
    count=0
    wt_msg = []
    for msg in msg_size_list:
        count=count+1
        if count==3:
            #print(msg)
            wt_msg.append(msg)
            count=0

    for i in netinfo['nodes']:
        if (i['data']['Layer']['Layer Index'] ) == 0:
            i['data']['Layer']['wt_remote_storage_msg_size'] = 0#total_parameter
            data_size = i['data']['Layer']['Input Tensor Dims'][0]['Tensor']['dims']
            data_size_split = data_size.split(';')
            data_size_list = [float(i) for i in data_size_split]
            numOfDataElement = np.prod(data_size_list)
            i['data']['Layer']['data_remote_storage_msg_size'] = Constants.bf_16*numOfDataElement
        else:
            i['data']['Layer']['wt_remote_storage_msg_size'] = 0
            i['data']['Layer']['data_remote_storage_msg_size'] = 0
            if (i['data']['Layer']['l_pass']) == 'upd':
                i['data']['Layer']['wt_remote_storage_msg_size'] = 0#total_parameter
        for index in range(len(unique_layerID)):
            if (i['data']['Layer']['Layer Index'] + 1) == unique_layerID[index]:
                #print((wt_msg[index]))
                i['data']['Layer']['wt_grad_msg_size'] =int(float(wt_msg[index]))
    with open(json_file, 'w') as f:
        json.dump(netinfo, f, indent=4)

    return

def _get_dataparallel_for_zero(total_tiles,model_split):
    return math.ceil(total_tiles/model_split)

def _get_optimizer_LayerID_for_zero (json_file):
    with open(json_file) as fin:
        netinfo = json.load(fin)
        total_parameter = 0
        for i in netinfo['nodes']:
            total_parameter = total_parameter+float(i['data']['Layer']['wt_grad_msg_size'])
            if (i['data']['Layer']['l_pass'])=='upd':
                layer_id= i['data']['Layer']['Layer Index']
                # print(layer_id)
                print("total_parameter zero:",total_parameter)
    return layer_id+1,math.ceil(total_parameter)

def _get_LayerID_for_zero_stage2_fused(json_file,data_parallel):
    with open(json_file) as fin:
        netinfo = json.load(fin)
        layer_upd_id,total_parameter = _get_optimizer_LayerID_for_zero(json_file)
        parameter_per_data_parallel =  math.ceil(total_parameter/data_parallel)
        #print(parameter_per_data_parallel)
        weight_for_comms = 0
        zero_2= []
        max_weight = parameter_per_data_parallel
        for i in netinfo['nodes']:
            if (i['data']['Layer']['l_pass'])=='bwd':
                weight_for_comms = weight_for_comms + float(i['data']['Layer']['wt_grad_msg_size'])
                layer_id= i['data']['Layer']['Layer Index']
                if layer_id==(layer_upd_id-2):
                    temp = {'layer_id': layer_id + 1, 'weight_for_comms': math.ceil(weight_for_comms)}
                    #max_weight= max(max_weight,math.ceil(weight_for_comms))
                    zero_2.append(temp)
                    weight_for_comms = 0
                else:
                    if weight_for_comms>=parameter_per_data_parallel:
                        temp={'layer_id':layer_id+1,'weight_for_comms':math.ceil(parameter_per_data_parallel)}
                        #max_weight = max(max_weight, math.ceil(weight_for_comms))
                        zero_2.append(temp)
                        weight_for_comms=weight_for_comms-parameter_per_data_parallel
                #print(layer_id)
        # print(zero_2)
        # print(max_weight)
        print("Data Parallel Supported by model:",len(zero_2))
        if len(zero_2) != data_parallel:
            raise SystemExit('Error: Zero2 Not supported')
    return zero_2,max_weight

def _get_LayerID_for_zero_stage2(json_file,data_parallel):
    with open(json_file) as fin:
        netinfo = json.load(fin)
        layer_upd_id,total_parameter = _get_optimizer_LayerID_for_zero(json_file)
        parameter_per_data_parallel =  math.ceil(total_parameter/data_parallel)
        weight_for_comms = 0
        zero_2= []
        max_weight = parameter_per_data_parallel
        for i in netinfo['nodes']:
            if (i['data']['Layer']['l_pass'])=='bwd-w':
                weight_for_comms = weight_for_comms + float(i['data']['Layer']['wt_grad_msg_size'])
                layer_id = i['data']['Layer']['Layer Index']
                if float(i['data']['Layer']['wt_grad_msg_size']) != 0:
                    temp = {'layer_id': layer_id + 1,
                            'weight_for_comms': math.ceil(float(i['data']['Layer']['wt_grad_msg_size'])),
                            'comms_type':"reduce"}
                    if layer_id==(layer_upd_id-2):
                        weight_for_comms = 0
                    else:
                        if weight_for_comms>=parameter_per_data_parallel:
                            weight_for_comms=weight_for_comms-parameter_per_data_parallel
                            temp = {'layer_id': layer_id + 1,
                                    'weight_for_comms': math.ceil(float(i['data']['Layer']['wt_grad_msg_size'])),
                                    'comms_type': "reduce"}
                    zero_2.append(temp)
                    #print(layer_id)
        # print(zero_2)
        # print(max_weight)
        print("Data Parallel Supported by model:",len(zero_2))
        # if len(zero_2) != data_parallel:
        #     raise SystemExit('Error: Zero2 Not supported')
    return zero_2,total_parameter

def _get_LayerID_for_zero_inf(json_file,data_parallel):
    with open(json_file) as fin:
        netinfo = json.load(fin)
        layer_upd_id,total_parameter = _get_optimizer_LayerID_for_zero(json_file)
        zero_inf = []
        for i in netinfo['nodes']:
            if (i['data']['Layer']['l_pass'])=='fwd' or (i['data']['Layer']['l_pass'])=='bwd-w' or (i['data']['Layer']['l_pass'])=='bwd-d':
                layer_id = i['data']['Layer']['Layer Index']
                if float(i['data']['Layer']['wt_grad_msg_size']) != 0:
                    temp = {'layer_id': layer_id + 1,
                            'weight_for_comms': math.ceil(float(i['data']['Layer']['wt_grad_msg_size'])),
                            'comms_type':"allgather"}

                    zero_inf.append(temp)

        #print("Data Parallel Supported by model:",len(zero_inf))
    return zero_inf,total_parameter

def _update_comms_zero2(zero2_list,total_parameter,layer_ID_list,msg_size_list,algo_list,msg_pass_type_list,Data_parallel_Zero):
    layer_upd_id=(zero2_list[-1]['layer_id'])+1

    for i in range(len(layer_ID_list)):
        if msg_pass_type_list[i] == "WT_GRAD":
            msg_size_list[i] = 0  # list['weight_for_comms']
            algo_list[i] = "0"
            msg_pass_type_list[i] = "0"

    count = 0
    for list in zero2_list:
        for i in range(len(layer_ID_list)):
            if (int(float(layer_ID_list[i])))==list['layer_id']:
                count = count + 1
                if count == 3:
                    count = 0
                    msg_size_list[i] = list['weight_for_comms']
                    algo_list[i] = list['comms_type']
                    msg_pass_type_list[i] = "WT_GRAD"
    count = 0
    for i in range(len(layer_ID_list)):
        if (int(float(layer_ID_list[i]))) == layer_upd_id:
            count = count + 1
            if count == 3:
                count = 0
                msg_size_list[i] = total_parameter / Data_parallel_Zero
                algo_list[i] = "allgather"
                msg_pass_type_list[i] = "WT_GRAD"
                # print((int(float(layer_ID_list[i]))))
                # print(algo_list[i])

    return msg_size_list,algo_list,msg_pass_type_list

def _update_comms_zero_inf(zero2_list,total_parameter,layer_ID_list,msg_size_list,algo_list,msg_pass_type_list,Data_parallel_Zero):
    layer_upd_id=(zero2_list[-1]['layer_id'])+1

    count = 0
    for list in zero2_list:
        for i in range(len(layer_ID_list)):
            if (int(float(layer_ID_list[i])))==list['layer_id']:
                count = count + 1
                if count == 3:
                    count = 0
                    msg_size_list[i] = list['weight_for_comms']
                    algo_list[i] = list['comms_type']
                    msg_pass_type_list[i] = "WT_GRAD"


    return msg_size_list,algo_list,msg_pass_type_list

def _update_comms_zero2_fused(zero2_list,total_parameter,layer_ID_list,msg_size_list,algo_list,msg_pass_type_list):
    layer_upd_id=(zero2_list[-1]['layer_id'])+1
    count = 0

    for i in range(len(layer_ID_list)):
        if msg_pass_type_list[i] == "WT_GRAD":
            msg_size_list[i] = 0  # list['weight_for_comms']
            algo_list[i] = "0"
            msg_pass_type_list[i] = "0"

    for list in zero2_list:
        for i in range(len(layer_ID_list)):
            if (int(float(layer_ID_list[i])))==list['layer_id']:
                count = count + 1
                if count == 3:
                    count = 0
                    msg_size_list[i] = list['weight_for_comms']
                    algo_list[i] = "reduce_scatter"
                    msg_pass_type_list[i] = "WT_GRAD"

    for i in range(len(layer_ID_list)):
        if (int(float(layer_ID_list[i]))) == layer_upd_id:
            count = count + 1
            if count == 3:
                count = 0
                msg_size_list[i] = total_parameter
                algo_list[i] = "allgather"
                msg_pass_type_list[i] = "WT_GRAD"
                # print((int(float(layer_ID_list[i]))))
                # print(algo_list[i])
                # print(msg_size_list[i])
    return msg_size_list,algo_list,msg_pass_type_list

def _update_comms_zero1(workload_graph,layer_ID_list,msg_size_list,algo_list,msg_pass_type_list,Data_parallel_Zero):
    opt_layer_id, total_parameter = _get_optimizer_LayerID_for_zero(workload_graph)
    print("Total Parameter size (B):", total_parameter)
    count = 0
    for i in range(len(layer_ID_list)):
        if (int(float(layer_ID_list[i]))) == (opt_layer_id - 1):
            count = count + 1
            if count == 3:
                count = 0
                msg_size_list[i] = total_parameter
                algo_list[i] = "reduce_scatter"
                msg_pass_type_list[i] = "WT_GRAD"
        elif (int(float(layer_ID_list[i]))) == (opt_layer_id):
            count = count + 1
            if count == 3:
                count = 0
                msg_size_list[i] = total_parameter / Data_parallel_Zero
                algo_list[i] = "allgather"
                msg_pass_type_list[i] = "WT_GRAD"
        else:
            count = count + 1
            if count == 3:
                count = 0
                msg_size_list[i] = 0
                algo_list[i] = "0"
                msg_pass_type_list[i] = "0"
    return msg_size_list,algo_list,msg_pass_type_list

def get_collective_comms_type(layer_ID_list,algo_list,msg_pass_type_list):
    unique_layer_ID = np.unique(np.array(layer_ID_list))
    fwd_collective_comms_type = [[]] * len(unique_layer_ID)
    inp_collective_comms_type = [[]] * len(unique_layer_ID)
    wt_collective_comms_type = [[]] * len(unique_layer_ID)
    for i in unique_layer_ID:
        idx = np.asscalar(np.where(unique_layer_ID == i)[0])
        fwd_collective_comms_type[idx] = [int(i), "0"]
        inp_collective_comms_type[idx] = [int(i), "0"]
        wt_collective_comms_type[idx] = [int(i), "0"]
        for j in range(0, len(layer_ID_list)):
            if i == layer_ID_list[j]:
                if msg_pass_type_list[j] == 'FWD':
                    fwd_collective_comms_type[idx] = [int(i), algo_list[j]]
                elif msg_pass_type_list[j] == 'INP_GRAD':
                    inp_collective_comms_type[idx] = [int(i), algo_list[j]]
                elif msg_pass_type_list[j] == 'WT_GRAD':
                    wt_collective_comms_type[idx] = [int(i), algo_list[j]]

    return fwd_collective_comms_type,inp_collective_comms_type,wt_collective_comms_type