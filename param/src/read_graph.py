import json
import numpy as np
import csv
import argparse




parser = argparse.ArgumentParser(description='Graph parser')
parser.add_argument('-c','--configfile', type=str)
parser.add_argument('-g','--jsonfile', type=str)
args = parser.parse_args()
print(args.configfile)
print(args.jsonfile)

config_file = args.configfile
json_file= args.jsonfile
json_file_out = ('..'+json_file.strip('.json')+'_out.json')

with open(config_file, mode='r') as infile:
    reader = csv.reader(infile)
    config_dict = {rows[0]:rows[1] for rows in reader}

data_parallel = 1
frequency_Ghz = float(config_dict["frequency_in_Ghz"])
data_parallel_nGPU = int(config_dict["no_of_cards"])
data_parallel_ntile_per_GPU = int(config_dict["no_of_tiles_card"])

# print(frequency_Ghz)
# print(data_parallel_nGPU)
# print(data_parallel_ntile_per_GPU)


with open(json_file) as fin:
       netinfo = json.load(fin)
# print(len(netinfo))
# for i in netinfo:
#        print(i)
no_of_layers = len(netinfo['layers'])
#print(no_of_layers)
no_of_items_per_layer = len(netinfo['layers'][0])
#print(no_of_items_per_layer)
#print(netinfo['layers'][0]['_paramSize'])

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


index=0
for i in netinfo['layers']:
        _paramSize[index] = i['_paramSize']
        _lname[index] = i['_lname']
        _lyrType[index] = i['_lyrType']
        _lyrId[index] = i['Layer Idx']+1
        _Perf_Cycles[index] = i['Perf Cycles']
        _Weight_Size[index] = i['Weight Size']


        index=index+1

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


#print (wt_grad_msg_size)

with open('../modelzoo/graph_resnet50.csv', mode='w') as output_file:
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
for i in netinfo['layers']:
    i['wt_grad_msg_size'] = _Weight_Size[index]
    i['fwd_pass_msg_size'] = fwd_pass_msg_size[index]
    i['inp_grad_msg_size'] = inp_grad_msg_size[index]
    i['fwd_pass_comp_time_ms'] = fwd_pass_comp_time[index]
    i['inp_grad_comp_time_ms'] = inp_grad_comp_time[index]
    i['wt_grad_comp_time_ms'] = wt_grad_comp_time[index]

    index = index + 1

with open(json_file_out, 'w') as f:
    json.dump(netinfo, f,indent=4)



perf_cycle_index = np.where(_Perf_Cycles != 0)
_paramSize_index = np.where(_paramSize != 0)
# fwd_pass_msg_size_index = np.where(fwd_pass_msg_size != 0)
# inp_grad_msg_size_index = np.where(inp_grad_msg_size != 0)
# wt_grad_msg_size_index = np.where(wt_grad_msg_size != 0)

with open('../modelzoo/compute_resnet50.csv', mode='w') as output_file:
    output_writer = csv.writer(output_file, delimiter=',')
    for i in np.nditer(perf_cycle_index):#
        #print(i)
        output_writer.writerow([_lyrId[i],fwd_pass_comp_time[i],inp_grad_comp_time[i],wt_grad_comp_time[i]])

with open('../modelzoo/workload_resnet50.csv', mode='w') as output_file:
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




print("                       ")
print("-----------------------------------------------------")
print("Graph Parsing Completed!!!")
print("Workload specific Compute Characteristic File and Workload specific config File Generated!!!")
print("-----------------------------------------------------")
print("                       ")