import os
import json
import numpy as np
from typing import Any

from .utils import *
import csv
import ctypes
import ntpath

csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))

# TODO remove this hack
CURRENT_FOLDER = os.path.dirname((os.path.abspath(__file__)))


# --------------------------------ARG Parser-----------------------------------------------------------------------------

def parse_graph(knobs, json_file, comp_stat_file, layer_stat_file):
    outFilePath = knobs['outFilePath']
    # print(json_file)
    # print(comp_stat_file)
    # print(layer_stat_file)
    if outFilePath is None or len(outFilePath) <= 0:
        outFilePath = './modelzoo/'

    json_file_out = (outFilePath + ntpath.basename(json_file).strip('.json') + '_out.json')

    data_parallel = knobs["data_parallel"]
    model_split = knobs["model_split"]
    use_buffer = knobs["use_buffer"]
    buffer_size = knobs["buffer_size"]
    frequency_Ghz = knobs["frequency_in_Ghz"]
    data_parallel_nGPU = knobs["num_PVC_per_host"]
    data_parallel_ntile_per_GPU = knobs["num_tiles_per_pvc"]
    B_float_16_2B = 2

    if not knobs["data_parallel"]:
        if knobs["model_split"] == 1: #handeling zero infinity
            fwd_split = []
            bwd_split = []
        else:
            # TODO : fix this path
            fwd_split, bwd_split = model_split_file_read(knobs["graph_split_csv"])

    f = open(json_file, "r")  # type: Any
    json_file_invalid = f.read()
    json_file_valid = json_file_invalid.split('=')[1]
    netinfo = json.loads(json_file_valid)

    # with open(json_file,'r') as fin:
    #     netinfo = json.load(fin)
    # # print(len(netinfo))
    # # for i in netinfo:
    # #         print(i)
    no_of_layers = len(netinfo['nodes'])
    # print(no_of_layers)
    # no_of_items_per_layer = len(netinfo['nodes'][0])
    # # print(no_of_items_per_layer)

    with open(layer_stat_file) as fin1:
        layer_stat = [row for row in csv.DictReader(fin1)]

    with open(comp_stat_file) as fin2:
        comp_stat = [row for row in csv.DictReader(fin2)]
    #print((comp_stat[0]))
    #print(comp_stat[0]['projTimeMsec'])
    # print(layer_stat[0]['Weight Size (Ki)'])

    _paramSize = np.zeros(no_of_layers)
    _lname = np.zeros([no_of_layers], dtype=object)
    _lyrType = np.zeros([no_of_layers], dtype=object)
    _lyrId = np.zeros(no_of_layers)
    _Perf_Cycles = np.zeros(no_of_layers)
    _Weight_Size = np.zeros(no_of_layers)
    gather_type = np.zeros([no_of_layers], dtype=object)
    if not knobs["data_parallel"]:
        fwd_gather_type = np.zeros([no_of_layers], dtype=object)
        inp_gather_type = np.zeros([no_of_layers], dtype=object)
        wt_gather_type = np.zeros([no_of_layers], dtype=object)
    wt_grad_msg_size = np.zeros(no_of_layers)
    bp_layer_name = [0]*no_of_layers
    inp_grad_msg_size = np.zeros(no_of_layers)
    fwd_pass_msg_size = np.zeros(no_of_layers)
    wt_grad_comp_time = np.zeros(no_of_layers)
    inp_grad_comp_time = np.zeros(no_of_layers)
    fwd_pass_comp_time = np.zeros(no_of_layers)
    _lpass = np.zeros([no_of_layers], dtype=object)
    _dict = np.zeros([no_of_layers], dtype=object)
    Output_Size = np.zeros(no_of_layers)

    index = 0
    for i in netinfo['nodes']:
        if knobs["data_parallel"]:
            _lyrId[index] = i['data']['Layer']['Layer Index'] + 1
            _lname[index] = i['data']['Layer']['Layer Name']
            _lyrType[index] = i['data']['Layer']['Layer Type']
            _paramSize[index] = float(layer_stat[index]['Weight Size (Ki)']) * 1024
            _Weight_Size[index] = _paramSize[index]
            _lpass[index] = layer_stat[index]['Pass']
            try:
                _Perf_Cycles[index] = (float(comp_stat[index]['projTimeMsec']))/1000*(1000000000 * frequency_Ghz)
            except ValueError:
                _Perf_Cycles[index] = 0
            Output_Size[index] = float(layer_stat[index]['Output Tensor Size (Ki)']) * 1024

            if _lpass[index] == "fwd":
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                wt_grad_msg_size[index] = 0
                gather_type[index] = 0
                fwd_pass_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                inp_grad_comp_time[index] = 0
                wt_grad_comp_time[index] = 0
            elif _lpass[index] == "bwd-w" or _lpass[index] == "bwd-d":
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                wt_grad_msg_size[index] = 0#_Weight_Size[index]
                fwd_pass_comp_time[index] = 0
                if _lpass[index] == "bwd-d":
                    inp_grad_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                    wt_grad_comp_time[index] = 0
                    gather_type[index] = 0
                else:
                    inp_grad_comp_time[index] = 0  # _Perf_Cycles[index] * 1000 / 2 / (1000000000 * frequency_Ghz)
                    if _Perf_Cycles[index]> 0:
                        wt_grad_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                        wt_grad_msg_size[index] = Output_Size[index]
                        gather_type[index] = "allreduce"
            else:
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                wt_grad_msg_size[index] = 0
                gather_type[index] = 0
                fwd_pass_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                inp_grad_comp_time[index] = 0
                wt_grad_comp_time[index] = 0
            index = index + 1
        else:
            _lyrId[index] = i['data']['Layer']['Layer Index'] + 1
            _lname[index] = i['data']['Layer']['Layer Name']
            _lyrType[index] = i['data']['Layer']['Layer Type']
            _paramSize[index] = float(layer_stat[index]['Weight Size (Ki)']) * 1024
            _Weight_Size[index] = _paramSize[index]
            _lpass[index] = layer_stat[index]['Pass']
            try:
                _Perf_Cycles[index] = (float(comp_stat[index]['projTimeMsec']))/1000*(1000000000 * frequency_Ghz)
            except ValueError:
                _Perf_Cycles[index] = 0
            Output_Size[index] = float(layer_stat[index]['Output Tensor Size (Ki)']) * 1024

            #print(_lpass[index])
            if _lpass[index] == "fwd":
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                wt_grad_msg_size[index] = 0
                if knobs['ZeRO_type'] == 4:
                    wt_grad_msg_size[index] = _Weight_Size[index]
                fwd_gather_type[index] = 0
                fwd_pass_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                inp_grad_comp_time[index] = 0
                wt_grad_comp_time[index] = 0
                for item in fwd_split:
                    if (item["Name"] in _lname[index] and item["type"] == _lyrType[index]):
                        if (item["pick"]=="NA"):
                            # print(_lname[index])
                            fwd_pass_msg_size[index] = Output_Size[index]
                            fwd_gather_type[index] = item["comms_type"]

                            break
                        else:
                            outputTensors = i['data']['Layer']["Output Tensor Dims"]
                            for tensor in outputTensors:
                                if(tensor["Tensor"]["name"]==item["pick"]):
                                    dims = tensor["Tensor"]["dims"].split(";")
                                    B,W,H,C = map(float,dims)
                            fwd_pass_msg_size[index] = 2*B*W*H*C
                            fwd_gather_type[index]=item["comms_type"]
                            break
            elif _lpass[index] == "bwd-w" or _lpass[index] == "bwd-d":
                bp_layer_name[index]=_lname[index]
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                #wt_grad_msg_size[index] = _Weight_Size[index]
                fwd_pass_comp_time[index] = 0
                if _lpass[index] == "bwd-d":
                    inp_grad_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                    wt_grad_comp_time[index] = 0
                    wt_gather_type[index] = 0
                    if knobs['ZeRO_type'] == 4:
                        wt_grad_msg_size[index] = _Weight_Size[index]
                    for item in bwd_split:
                        if (item["Name"] in _lname[index] and item["type"] == _lyrType[index]):
                            if (item["pick"]=="NA"):
                                # print(_lname[index])
                                inp_grad_msg_size[index] = Output_Size[index]
                                inp_gather_type[index] = item["comms_type"]
                                break
                            else:
                                outputTensors = i['data']['Layer']["Output Tensor Dims"]
                                for tensor in outputTensors:
                                    if(tensor["Tensor"]["name"]==item["pick"]):
                                        dims = tensor["Tensor"]["dims"].split(";")
                                        B,W,H,C = map(float,dims)
                                inp_grad_msg_size[index] = B_float_16_2B*B*W*H*C
                                inp_gather_type[index]=item["comms_type"]
                                break

                else:
                    inp_grad_comp_time[index] = 0#_Perf_Cycles[index] * 1000 / 2 / (1000000000 * frequency_Ghz)
                    inp_gather_type[index] = 0
                    if _Perf_Cycles[index] > 0:
                        wt_grad_comp_time[index] = _Perf_Cycles[index] * 1000  / (1000000000 * frequency_Ghz)
                        wt_gather_type[index] = "allreduce"
                        wt_grad_msg_size[index] = Output_Size[index]
                        for item in bwd_split:
                            if(item["Name"] in _lname[index] and item["type"]==_lyrType[index]):
                                print(item["Name"])
                                if(item["pass"]=="INP_GRAD"):
                                    if(item["pick"]=="NA"):
                                        inp_grad_msg_size[index] = Output_Size[index]
                                        inp_gather_type[index] = item["comms_type"]
                                        break
                                    else:
                                        outputTensors = i['data']['Layer']["Output Tensor Dims"]
                                        for tensor in outputTensors:
                                            if(tensor["Tensor"]["name"]==item["pick"]):
                                                dims = tensor["Tensor"]["dims"].split(";")
                                                B,W,H,C = map(float,dims)
                                        inp_grad_msg_size[index] = B_float_16_2B*B*W*H*C
                                        inp_gather_type[index]=item["comms_type"]
                                        break
                                elif(item["pass"]=="WT_GRAD"):
                                    wt_gather_type[index]=item["comms_type"]
                                    break
            else:
                fwd_pass_msg_size[index] = 0
                inp_grad_msg_size[index] = 0
                bp_layer_name[index]='0'
                wt_grad_msg_size[index] = 0
                gather_type[index] = 0
                fwd_pass_comp_time[index] = _Perf_Cycles[index] * 1000 / (1000000000 * frequency_Ghz)
                inp_grad_comp_time[index] = 0
                wt_grad_comp_time[index] = 0

            index = index + 1


    with open('{}graph.csv'.format(outFilePath), mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        output_writer.writerow(np.append(['_lyrId'], _lyrId))
        output_writer.writerow(np.append(['_lname'], _lname))
        output_writer.writerow(np.append(['_lyrType'], _lyrType))
        output_writer.writerow(np.append(['_paramSize'], _paramSize))
        output_writer.writerow(np.append(['_Perf_Cycles'], _Perf_Cycles))
        output_writer.writerow(np.append(['_Weight_Size'], _Weight_Size))
        # output_writer.writerow(np.append(['gather_type'],gather_type))
        output_writer.writerow(np.append(['fwd_pass_msg_size'], fwd_pass_msg_size))
        output_writer.writerow(np.append(['inp_grad_msg_size'], inp_grad_msg_size))
        output_writer.writerow(np.append(['wt_grad_msg_size'], wt_grad_msg_size))
        output_writer.writerow(np.append(['fwd_pass_comp_time_ms'], fwd_pass_comp_time))
        output_writer.writerow(np.append(['inp_grad_comp_time_ms'], inp_grad_comp_time))
        output_writer.writerow(np.append(['wt_grad_comp_time_ms'], wt_grad_comp_time))

    

    #Compression
    comms_bits = 16
    compression_enable=False
    fwd_Comp_to_X_bit = 8
    inp_Comp_to_X_bit = 8
    wt_grad_Comp_to_X_bit = 8

    if compression_enable:
        fwd_pass_msg_size=fwd_pass_msg_size/(comms_bits/fwd_Comp_to_X_bit)
        inp_grad_msg_size = inp_grad_msg_size/(comms_bits/inp_Comp_to_X_bit)
        wt_grad_msg_size = wt_grad_msg_size / (comms_bits / wt_grad_Comp_to_X_bit)
        netinfo["Comms_Compression"] = {"Enable":True,
                                        "Original_comms_bit":comms_bits,
                                        "fwd_Comp_to_X_bit":fwd_Comp_to_X_bit,
                                        "inp_Comp_to_X_bit":inp_Comp_to_X_bit,
                                        "wt_grad_Comp_to_X_bit":wt_grad_Comp_to_X_bit}
    else:
        netinfo["Comms_Compression"] = {"Enable": False,
                                        "Original_comms_bit": comms_bits,
                                        "fwd_Comp_to_X_bit": comms_bits,
                                        "inp_Comp_to_X_bit": comms_bits,
                                        "wt_grad_Comp_to_X_bit": comms_bits}

    

    perf_cycle_index = np.where(_Perf_Cycles != -1)
    # print(perf_cycle_index)
    # _paramSize_index = np.where(_paramSize != 0)

    if knobs["data_parallel"]:
        # -----------------------Buffer--------------------------------------------------------------
        if use_buffer == 1:
            # print(np.sum(wt_grad_msg_size))
            # print((wt_grad_msg_size))
            counter = 0
            weight_index=[]
            i_list = []
            for i in range(len(wt_grad_msg_size)):
                if wt_grad_msg_size[i] != 0 :#and bp_layer_name[i].find("mlp")>0:
                    weight_index.append(i)
                    i_list.append(i)
                    counter = counter + wt_grad_msg_size[i]
                    if counter >= buffer_size:
                        residue = counter-buffer_size
                        wt_grad_msg_size[i] = buffer_size
                        for value in i_list[:-1]:
                            wt_grad_msg_size[value] = 0
                        counter = residue
                        i_list = []

            for value in i_list:
                wt_grad_msg_size[value] = 0
            wt_grad_msg_size[weight_index[-1]]+=counter

        # print(np.sum(wt_grad_msg_size))
        # print((wt_grad_msg_size))
        # --------------------------------------------------------------------------------------------

        index = 0
        for i in netinfo['nodes']:
            i['data']['Layer']['l_pass'] = _lpass[index]
            i['data']['Layer']['wt_grad_msg_size'] = wt_grad_msg_size[index]
            i['data']['Layer']['fwd_pass_msg_size'] = fwd_pass_msg_size[index]
            i['data']['Layer']['inp_grad_msg_size'] = inp_grad_msg_size[index]
            i['data']['Layer']['fwd_pass_comp_cycles'] = float(fwd_pass_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            i['data']['Layer']['inp_grad_comp_cycles'] = float(inp_grad_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            i['data']['Layer']['wt_grad_comp_cycles'] = float(wt_grad_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            index = index + 1
    
        with open(json_file_out, 'w') as f:
            json.dump(netinfo, f, indent=4)
            
        with open('{}compute.csv'.format(outFilePath), mode='w') as output_file:
            output_writer = csv.writer(output_file, delimiter=',')
            for i in np.nditer(perf_cycle_index):  #
                # print(i)
                output_writer.writerow([_lyrId[i], fwd_pass_comp_time[i], inp_grad_comp_time[i], wt_grad_comp_time[i]])

        with open('{}comms.csv'.format(outFilePath), mode='w') as output_file:
            output_writer = csv.writer(output_file, delimiter=',')
            output_writer.writerow(
                ['Msg_size', 'algo', 'No_of_GPU', 'No_of_tile_per_socket', 'MSG_PASS_Type', 'layer_ID'])
            for i in np.nditer(perf_cycle_index):
                fwd_pass = "0"
                int_pass = "0"
                wt_pass = "0"
                if fwd_pass_msg_size[i] != 0:
                    fwd_pass = "FWD"
                output_writer.writerow(
                    [fwd_pass_msg_size[i], gather_type[i], data_parallel_nGPU, data_parallel_ntile_per_GPU,
                     fwd_pass, _lyrId[i]])
                if inp_grad_msg_size[i] != 0:
                    int_pass = "INP_GRAD"
                output_writer.writerow(
                    [inp_grad_msg_size[i], gather_type[i], data_parallel_nGPU, data_parallel_ntile_per_GPU,
                     int_pass, _lyrId[i]])
                if wt_grad_msg_size[i] != 0:
                    wt_pass = "WT_GRAD"
                output_writer.writerow(
                    [wt_grad_msg_size[i], gather_type[i], data_parallel_nGPU, data_parallel_ntile_per_GPU,
                     wt_pass, _lyrId[i]])
    else:
        if(not knobs["data_parallel"] and knobs["hybrid_model"]):
            if use_buffer == 1:
            # print(np.sum(wt_grad_msg_size))
            # print((wt_grad_msg_size))
                counter = 0
                weight_index=[]
                i_list = []
                for i in range(len(wt_grad_msg_size)):
                    if wt_grad_msg_size[i] != 0 and bp_layer_name[i].find("mlp")>0:
                        weight_index.append(i)
                        i_list.append(i)
                        counter = counter + wt_grad_msg_size[i]
                        if counter >= buffer_size:
                            residue = counter-buffer_size
                            wt_grad_msg_size[i] = buffer_size
                            for value in i_list[:-1]:
                                wt_grad_msg_size[value] = 0
                            counter = residue
                            i_list = []

                for value in i_list:
                    wt_grad_msg_size[value] = 0
                wt_grad_msg_size[weight_index[-1]]+=counter

        index = 0
        for i in netinfo['nodes']:
            i['data']['Layer']['l_pass'] = _lpass[index]
            i['data']['Layer']['wt_grad_msg_size'] = wt_grad_msg_size[index]
            i['data']['Layer']['fwd_pass_msg_size'] = fwd_pass_msg_size[index]
            i['data']['Layer']['inp_grad_msg_size'] = inp_grad_msg_size[index]
            i['data']['Layer']['fwd_pass_comp_cycles'] = float(fwd_pass_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            i['data']['Layer']['inp_grad_comp_cycles'] = float(inp_grad_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            i['data']['Layer']['wt_grad_comp_cycles'] = float(wt_grad_comp_time[index]) * (
                        1000000000 * frequency_Ghz) / 1000
            i['data']['Layer']['Weight'] = float(layer_stat[index]['Weight Size (Ki)']) * 1024
            i['data']['Layer']['Input'] = float(layer_stat[index]['Input Tensor Size (Ki)']) * 1024
            i['data']['Layer']['Output'] = float(layer_stat[index]['Output Tensor Size (Ki)']) * 1024
            index = index + 1
    
        with open(json_file_out, 'w') as f:
            json.dump(netinfo, f, indent=4)
        
        if model_split <= (data_parallel_nGPU * data_parallel_ntile_per_GPU):
            fwd_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
            inp_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
            if model_split < (data_parallel_nGPU * data_parallel_ntile_per_GPU):
                wt_nCards_scaleup = data_parallel_nGPU / (model_split / data_parallel_ntile_per_GPU)
                if knobs['ZeRO_type'] == 4: #handeling zero infinity
                    wt_data_parallel_ntile_per_GPU = data_parallel_ntile_per_GPU
                else:
                    wt_data_parallel_ntile_per_GPU = 1 # data_parallel_ntile_per_GPU
            else:
                if knobs["hybrid_model"]:
                    wt_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
                    wt_data_parallel_ntile_per_GPU = data_parallel_ntile_per_GPU
                else:
                    wt_nCards_scaleup = 0
                    wt_data_parallel_ntile_per_GPU = 0
        else:
            fwd_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
            inp_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
            if knobs["hybrid_model"]:
                wt_nCards_scaleup = model_split / data_parallel_ntile_per_GPU
                wt_data_parallel_ntile_per_GPU = data_parallel_ntile_per_GPU
            else:
                wt_nCards_scaleup = 0
                wt_data_parallel_ntile_per_GPU = 0
        with open('{}compute.csv'.format(outFilePath), mode='w') as output_file:
            output_writer = csv.writer(output_file, delimiter=',')
            for i in np.nditer(perf_cycle_index):  #
                # print(i)
                output_writer.writerow([_lyrId[i], fwd_pass_comp_time[i], inp_grad_comp_time[i], wt_grad_comp_time[i]])

        with open('{}comms.csv'.format(outFilePath), mode='w') as output_file:
            output_writer = csv.writer(output_file, delimiter=',')
            output_writer.writerow(
                ['Msg_size', 'algo', 'No_of_GPU', 'No_of_tile_per_socket', 'MSG_PASS_Type', 'layer_ID'])
            for i in np.nditer(perf_cycle_index):
                fwd_pass = "0"
                int_pass = "0"
                wt_pass = "0"
                if fwd_pass_msg_size[i] != 0:
                    fwd_pass = "FWD"
                output_writer.writerow(
                    [fwd_pass_msg_size[i], fwd_gather_type[i], int(fwd_nCards_scaleup), data_parallel_ntile_per_GPU,
                     fwd_pass, _lyrId[i]])
                if inp_grad_msg_size[i] != 0:
                    int_pass = "INP_GRAD"
                output_writer.writerow(
                    [inp_grad_msg_size[i], inp_gather_type[i], int(inp_nCards_scaleup), data_parallel_ntile_per_GPU,
                     int_pass, _lyrId[i]])
                if wt_grad_msg_size[i] != 0:
                    wt_pass = "WT_GRAD"
                output_writer.writerow(
                    [wt_grad_msg_size[i], wt_gather_type[i], int(wt_nCards_scaleup), wt_data_parallel_ntile_per_GPU,
                     wt_pass, _lyrId[i]])

    # print("                       ")
    # print("-----------------------------------------------------")
    # print("Graph Parsing Completed!!!")
    # print("Workload specific Compute Characteristic File and Workload specific config File Generated!!!")
    # print("-----------------------------------------------------")
    # print("                       ")
