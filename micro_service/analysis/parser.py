import json
import csv
import numpy as np
import argparse

#--------------------------------ARG Parser-----------------------------------------------------------------------------

def parse_graph(config_dict, json_file, comp_stat_file, layer_stat_file):

    outFilePath = config_dict['outFilePath']
    if outFilePath is None or len(outFilePath) <= 0:
        outFilePath = './modelzoo/'

    json_file_out = (outFilePath + json_file.split('/')[-1].strip('.json')+'_out.json')
    # print(json_file_out)
    #-----------------------------------------------------------------------------------------------------------------------



    data_parallel = 1
    use_buffer = int(config_dict["use_buffer"])
    buffer_size = int(config_dict["buffer_size"])
    frequency_Ghz = float(config_dict["frequency_in_Ghz"])
    data_parallel_nGPU = int(config_dict["no_of_cards"])
    data_parallel_ntile_per_GPU = int(config_dict["no_of_tiles_card"])
    outFilePath = config_dict['outFilePath']

    f = open(json_file, "r")
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
    #print(comp_stat[0]['Perf Cycles'])
    #print(layer_stat[0]['Weight Size (Ki)'])

    _paramSize=np.zeros(no_of_layers)
    _lname=np.zeros([no_of_layers],dtype=object)
    _lyrType=np.zeros([no_of_layers],dtype=object)
    _lyrId = np.zeros(no_of_layers)
    _Perf_Cycles = np.zeros(no_of_layers)
    _Weight_Size = np.zeros(no_of_layers)
    gather_type= np.zeros([no_of_layers],dtype=object)
    wt_grad_msg_size= np.zeros(no_of_layers)
    inp_grad_msg_size= np.zeros(no_of_layers)
    fwd_pass_msg_size = np.zeros(no_of_layers)
    wt_grad_comp_time = np.zeros(no_of_layers)
    inp_grad_comp_time = np.zeros(no_of_layers)
    fwd_pass_comp_time = np.zeros(no_of_layers)
    #
    index=0
    for i in netinfo['nodes']:
            _paramSize[index] = float(layer_stat[index]['Weight Size (Ki)'])*1024
            _lname[index] = i['data']['Layer']['Layer Name']
            _lyrType[index] = i['data']['Layer']['Layer Type']
            _lyrId[index] = i['data']['Layer']['Layer Index']+1
            _Perf_Cycles[index] = comp_stat[index]['Perf Cycles']
            _Weight_Size[index] = _paramSize[index]
            index = index + 1

    weight_index = np.where(_Weight_Size != 0)

    if data_parallel==1:
        np.put(gather_type, weight_index, 'allreduce')
        wt_grad_msg_size=_Weight_Size
        fwd_pass_comp_time = (_Perf_Cycles*1000/(1000000000*frequency_Ghz))
        inp_grad_comp_time = (_Perf_Cycles*1000/(1000000000*frequency_Ghz))
        wt_grad_comp_time =  (_Perf_Cycles*1000/(1000000000*frequency_Ghz))
        #np.put(fwd_pass_comp_time, np.where(_Weight_Size == 0), 0)
        np.put(inp_grad_comp_time, np.where(_Weight_Size == 0), 0)
        np.put(wt_grad_comp_time, np.where(_Weight_Size == 0), 0)

    with open('{}graph.csv'.format(outFilePath), mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        output_writer.writerow(np.append(['_lyrId'],_lyrId))
        output_writer.writerow(np.append(['_lname'],_lname))
        output_writer.writerow(np.append(['_lyrType'],_lyrType))
        output_writer.writerow(np.append(['_paramSize'],_paramSize))
        output_writer.writerow(np.append(['_Perf_Cycles'],_Perf_Cycles))
        output_writer.writerow(np.append(['_Weight_Size'],_Weight_Size))
        output_writer.writerow(np.append(['gather_type'],gather_type))
        output_writer.writerow(np.append(['fwd_pass_msg_size'],fwd_pass_msg_size))
        output_writer.writerow(np.append(['inp_grad_msg_size'], inp_grad_msg_size))
        output_writer.writerow(np.append(['wt_grad_msg_size'], wt_grad_msg_size))
        output_writer.writerow(np.append(['fwd_pass_comp_time'],fwd_pass_comp_time))
        output_writer.writerow(np.append(['inp_grad_comp_time'],inp_grad_comp_time))
        output_writer.writerow(np.append(['wt_grad_comp_time'],wt_grad_comp_time))

    index=0
    for i in netinfo['nodes']:
        i['data']['Layer']['wt_grad_msg_size'] = _Weight_Size[index]
        i['data']['Layer']['fwd_pass_msg_size'] = fwd_pass_msg_size[index]
        i['data']['Layer']['inp_grad_msg_size'] = inp_grad_msg_size[index]
        i['data']['Layer']['fwd_pass_comp_cycles'] = float(fwd_pass_comp_time[index])*(1000000000*frequency_Ghz)/1000
        i['data']['Layer']['inp_grad_comp_cycles'] = float(inp_grad_comp_time[index])*(1000000000*frequency_Ghz)/1000
        i['data']['Layer']['wt_grad_comp_cycles'] = float(wt_grad_comp_time[index])*(1000000000*frequency_Ghz)/1000


        index = index + 1

    with open(json_file_out, 'w') as f:
        json.dump(netinfo, f,indent=4)

    perf_cycle_index = np.where(_Perf_Cycles != 0)
    _paramSize_index = np.where(_paramSize != 0)
    # fwd_pass_msg_size_index = np.where(fwd_pass_msg_size != 0)
    # inp_grad_msg_size_index = np.where(inp_grad_msg_size != 0)
    # wt_grad_msg_size_index = np.where(wt_grad_msg_size != 0)

    #-----------------------Buffer--------------------------------------------------------------
    if use_buffer==1:
        # print(np.sum(wt_grad_msg_size))
        # print((wt_grad_msg_size))
        count=0
        sum=0
        i_list=[]
        for i in  reversed(range(len(wt_grad_msg_size))):
            if wt_grad_msg_size[i]!=0:
                i_list_minus1 = list(i_list)
                i_list.extend([i])
                sum_minus_one = sum
                sum = sum+wt_grad_msg_size[i]
                if sum > buffer_size:
                    #index =  i_list_minus1.pop()
                    wt_grad_msg_size[i] = sum#sum_minus_one
                    for value in i_list_minus1:
                        wt_grad_msg_size[value] =0
                    sum=0#wt_grad_msg_size[i]
                    i_list = []

        #index = i_list.pop()
        for value in i_list:
            wt_grad_msg_size[value] = 0
        wt_grad_msg_size[i] = sum

    # print(np.sum(wt_grad_msg_size))
    # print((wt_grad_msg_size))
    #--------------------------------------------------------------------------------------------

    with open('{}compute.csv'.format(outFilePath), mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        for i in np.nditer(perf_cycle_index):#
            #print(i)
            output_writer.writerow([_lyrId[i],fwd_pass_comp_time[i],inp_grad_comp_time[i],wt_grad_comp_time[i]])

    with open('{}comms.csv'.format(outFilePath), mode='w') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        output_writer.writerow(['Msg_size','algo','No_of_GPU','No_of_tile_per_socket','MSG_PASS_Type','layer_ID'])
        for i in np.nditer(perf_cycle_index):
            fwd_pass = "0"
            int_pass = "0"
            wt_pass = "0"
            if fwd_pass_msg_size[i] != 0:
                fwd_pass = "FWD"
            output_writer.writerow([fwd_pass_msg_size[i],gather_type[i],data_parallel_nGPU,data_parallel_ntile_per_GPU,
                                    fwd_pass,_lyrId[i]])
            if inp_grad_msg_size[i] != 0:
                int_pass = "INP_GRAD"
            output_writer.writerow([inp_grad_msg_size[i],gather_type[i],data_parallel_nGPU,data_parallel_ntile_per_GPU,
                                    int_pass,_lyrId[i]])
            if wt_grad_msg_size[i] != 0:
                wt_pass = "WT_GRAD"
            output_writer.writerow([wt_grad_msg_size[i],gather_type[i],data_parallel_nGPU,data_parallel_ntile_per_GPU,
                                    wt_pass,_lyrId[i]])




    # print("                       ")
    # print("-----------------------------------------------------")
    # print("Graph Parsing Completed!!!")
    # print("Workload specific Compute Characteristic File and Workload specific config File Generated!!!")
    # print("-----------------------------------------------------")
    # print("                       ")