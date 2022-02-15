import csv
from .comms import *
import argparse




parser = argparse.ArgumentParser(description='Comms wrapper')
parser.add_argument('-c','--configfile', type=str)
parser.add_argument('-m','--msgsize', type=str)
args = parser.parse_args()
#print(args.configfile)
config_file = args.configfile
msg_size = args.msgsize

with open(config_file, mode='r') as infile:
    reader = csv.reader(infile)
    config_dict = {rows[0]:rows[1] for rows in reader}    
# for i in config_dict:
#     print(i)
#     print(config_dict[i])

msg_size_list = [msg_size]
algo_list = ['a2a']
no_socket_list = [int(config_dict["no_of_cards"])]
tile_per_socket_list = [int(config_dict["no_of_tiles_card"])]


out=[[]]*len(msg_size_list)
scaleout= [[]]*len(msg_size_list)
Final_Total_time_us_list=[]#*len(msg_size_list)
#print(len(out))
#print(len(Final_Total_time_us_list))
#print(out)
for i in range(len(msg_size_list)):
    #print (i)
    coms_input_dict = {"msg_size":msg_size_list[i],
                       "no_socket":no_socket_list[i],
                       "tile_per_socket":tile_per_socket_list[i],
                       }

    #print(coms_input_dict)
    compute = comms.Comms(coms_input_dict,config_dict)

    if  algo_list[i] == "allreduce":
        #print("allreduce")
        out[i]=compute.allreduce()
        #scaleout[i] = compute.scaleout()


    elif algo_list[i] == "allgather":
        #print("allgather")
        out[i]=compute.allgather()
        #scaleout[i] = [0,0,0,0,0,0]

    elif algo_list[i] == "a2a":
        #print("a2a")
        out[i]=compute.all_to_all()
        #scaleout[i] = [0,0,0,0,0,0]

    elif algo_list[i] == "0":
        #print("allgather")
        out[i]=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        #scaleout[i] = [0,0,0,0,0,0]

    #print(msg_size_list[i])
    #print([out[i][7],out[i][8],out[i][9]])
    print('mdfi_latency', 'scale_up_latency', 'local_read_mdfi',
               'local_read_scale_up', 'local_write_scale_up',
               'remote_write_mdfi', 'remote_write_scale_up', 'mdfi_time_us',
               'scale_up_time_us', 'total_time_us',
               'mdfi_achieved_BW', 'scale_up_achieved_BW', 'mdfi_latency_percentage',
               'mdfi_Local_R_W_sum_percentage',
               'mdfi_write_percentage', 'percentage_peak_BW_mdfi',
               'scale_up_latency_percentage', 'scale_up_local_R_W_sum_percentage',
               'scale_up_write_percentage', 'percentage_peak_BW_scale_up')
    print(out[i])
    #print(scaleout[i])
    #print(out[i][9])
    #Final_Total_time_us_list.append(out[i][9])




