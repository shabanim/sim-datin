import csv
from comms import *

def comms_wrapper(config_dict, workload_config, workload_compute, output_file_path, workload_graph, scale_out_flag=False, config_dict_scaleout=None):

    data_parallel = 0
    model_split = 48

    if scale_out_flag :
        config_dict['scaleout_type_wrt_HW'] = config_dict_scaleout["scaleout_type_wrt_HW"]
        config_dict['scale_out_flag'] = '1'
    else:
        config_dict['scale_out_flag'] = '0'
    #print(config_dict)
        config_dict['scaleout_type_wrt_HW'] = config_dict_scaleout["scaleout_type_wrt_HW"]
        config_dict['scale_out_flag'] = '1'


    # for i in config_dict:
    #     print(i)
    #     print(config_dict[i])



    with open(workload_config) as f:
        reader = csv.reader(f, delimiter=",")
        dataList = list(reader)
        msg_size_list = []
        algo_list = []
        no_socket_list = []
        tile_per_socket_list = []
        msg_pass_type_list = []
        layer_ID_list = []
        for row in dataList:
          #print(row[1])
          if len(row) > 0:
              msg_size_list.append((row[0].strip().split(' ')[-1]))
              algo_list.append((row[1].strip().split(' ')[-1]))
              no_socket_list.append((row[2].strip().split(' ')[-1]))
              tile_per_socket_list.append((row[3].strip().split(' ')[-1]))
              msg_pass_type_list.append((row[4].strip().split(' ')[-1]))
              layer_ID_list.append((row[5].strip().split(' ')[-1]))

    with open(workload_compute) as f:
        reader = csv.reader(f, delimiter=",")
        dataList = list(reader)
        compute_layer_id_list=[]
        compute_fwd_time_list=[]
        compute_bwd_time_list= []
        compute_wt_grad_time_list=[]
        for row in dataList:
            if len(row) > 0:
                compute_layer_id_list.append((row[0].strip().split(' ')[-1]))
                compute_fwd_time_list.append((row[1].strip().split(' ')[-1]))
                compute_bwd_time_list.append((row[2].strip().split(' ')[-1]))
                compute_wt_grad_time_list.append((row[3].strip().split(' ')[-1]))

    del msg_size_list[0]
    del algo_list[0]
    del no_socket_list[0]
    del tile_per_socket_list[0]
    del msg_pass_type_list[0]
    del layer_ID_list[0]

    #print(msg_size_list)
    # print(algo_list)
    #print(no_socket_list)
    # print(tile_per_socket_list)
    #print(msg_pass_type_list)
    #print(layer_ID_list)
    # print(compute_layer_id_list)
    # print(compute_fwd_time_list)
    # print(compute_bwd_time_list)
    # print(compute_wt_grad_time_list)

    compute_time = [[]]*len(compute_layer_id_list)
    for i in range(len(compute_layer_id_list)):
        compute_time[i]=[int(float(compute_layer_id_list[i])),float(compute_fwd_time_list[i]),float(compute_bwd_time_list[i]),
                         float(compute_wt_grad_time_list[i])]
        #print(compute_time[i])


    out=[[]]*len(msg_size_list)
    Final_Total_time_us_list=[]#*len(msg_size_list)
    #print(len(out))
    #print(len(Final_Total_time_us_list))
    #print(out)
    for i in range(len(msg_size_list)):
        #print (i)
        if data_parallel==1:
                    coms_input_dict = {"msg_size":msg_size_list[i],
                           "no_socket":no_socket_list[i],
                           "tile_per_socket":tile_per_socket_list[i],
                           }
        else:
            if int(no_socket_list[i])>=int(config_dict["no_of_cards"]):
                coms_input_dict = {"msg_size": msg_size_list[i],
                                   "no_socket": int(config_dict["no_of_cards"]),
                                   "tile_per_socket": tile_per_socket_list[i],
                                   }


        compute = Comms(coms_input_dict,config_dict)

        if int(no_socket_list[i])!=0:
            if  algo_list[i] == "allreduce":
                out[i]=compute.allreduce()

            elif algo_list[i] == "allgather":
                out[i]=compute.allgather()

            elif algo_list[i] == "a2a":
                out[i]=compute.all_to_all()

            elif algo_list[i] == "0":
                out[i]=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        else:
            out[i] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        #print(out)
        multiply_factor = 1 + float(config_dict["include_jitter_to_scaleup"])
        if scale_out_flag:
            if config_dict_scaleout['scaleout_type_wrt_HW']=='3':
                Final_Total_time_us_list.append(multiply_factor*out[i][7])
            else:
                Final_Total_time_us_list.append(multiply_factor*out[i][9])
        else:
            Final_Total_time_us_list.append(multiply_factor*out[i][9])


    out_table = np.asarray(out)
    #print(out_table[:,7:10])
    #print(Final_Total_time_us_list)

    # with open("out1.csv", "w", newline="") as f:
    #     writer = csv.writer(f)
    #     writer.writerows(out)

    layer_ID_list = list(map(float, layer_ID_list))
    layer_ID_list = list(map(int, layer_ID_list))
    unique_layer_ID = np.unique(np.array(layer_ID_list))
    #print(unique_layer_ID)
    #print(['Layer ID','FWD','INP_GRAD','WT_GRAD'])
    final_time =[[]]*len(unique_layer_ID)
    for i in unique_layer_ID:
        idx = np.asscalar(np.where(unique_layer_ID == i)[0])
        sum_FWD = 0.0
        sum_INP_GRAD = 0.0
        sum_WT_GRAD = 0.0
        sum_WT = 0.0
        for j in range (0,len(msg_size_list)):
          if i==layer_ID_list[j]:
            if msg_pass_type_list[j]=='FWD':
                sum_FWD = sum_FWD + float(Final_Total_time_us_list[j])
            elif msg_pass_type_list[j] == 'INP_GRAD':
                sum_INP_GRAD = sum_INP_GRAD + float(Final_Total_time_us_list[j])
            elif msg_pass_type_list[j] == 'WT_GRAD':
                sum_WT_GRAD = sum_WT_GRAD + float(Final_Total_time_us_list[j])

            sum_WT = sum_WT + float(msg_size_list[j])
        sum_FWD = sum_FWD/1000
        sum_INP_GRAD = sum_INP_GRAD/1000
        sum_WT_GRAD = sum_WT_GRAD/1000
        final_time[idx] = [i,sum_FWD,sum_INP_GRAD,sum_WT_GRAD,sum_WT]
        #print(final_time[idx])

    #--------------------------------------------------Scaleout-------------------------------------------------------------

    if scale_out_flag :
        multiply_factor_scaleout = 1 + float(config_dict_scaleout["include_jitter_to_scaleout"])
        print("Scaleout")
        if data_parallel == 1:
            config_dict_scaleout['num_tiles_per_pvc'] = config_dict["no_of_tiles_card"]
            config_dict_scaleout['num_PVC_per_host'] = config_dict["no_of_cards"]
            scaleout_time_fwd = [[]] * len(unique_layer_ID)
            scaleout_time_inp = [[]] * len(unique_layer_ID)
            scaleout_time_wt = [[]] * len(unique_layer_ID)
            scaleout_time = [[]] * len(unique_layer_ID)
            for i in unique_layer_ID:
                idx = np.asscalar(np.where(unique_layer_ID == i)[0])
                out=0
                #print(idx)
                for j in range(0, len(msg_size_list)):
                    if i == layer_ID_list[j]:
                        scaleout_time_fwd[idx] = [int(i), 0]
                        scaleout_time_inp[idx] = [int(i), 0]
                        scaleout_time_wt[idx] = [int(i), 0]
                        if msg_pass_type_list[j] == 'WT_GRAD':
                            #print(msg_size_list[j])
                            config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                            #print(config_dict_scaleout)
                            compute = Comms_scaleout(config_dict_scaleout)
                            out = compute.scaleout()
                            #print("Scaleout time(us):", out)
                scaleout_time[idx] = [int(i), multiply_factor_scaleout*out/1000]
                scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out / 1000]

        else:
            config_dict_scaleout['num_tiles_per_pvc'] = config_dict["no_of_tiles_card"]
            config_dict_scaleout['num_PVC_per_host'] = config_dict["no_of_cards"]
            scaleout_time_fwd = [[]] * len(unique_layer_ID)
            scaleout_time_inp = [[]] * len(unique_layer_ID)
            scaleout_time_wt = [[]] * len(unique_layer_ID)
            scaleout_time = [[]] * len(unique_layer_ID)
            total_nu_cards = config_dict_scaleout['num_pvc']
            nu_tiles = config_dict_scaleout['num_tiles_per_pvc']
            nu_cards= config_dict["no_of_cards"]
            for i in unique_layer_ID:
                idx = np.asscalar(np.where(unique_layer_ID == i)[0])
                out = 0

                for j in range(0, len(msg_size_list)):
                    if i == layer_ID_list[j]:
                        scaleout_time_fwd[idx] = [int(i), 0]
                        scaleout_time_inp[idx] = [int(i), 0]
                        scaleout_time_wt[idx] = [int(i), 0]
                        if msg_pass_type_list[j] == 'FWD':
                            if int(no_socket_list[j]) <= int(config_dict_scaleout['num_PVC_per_host']):
                                #config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                scaleout_time_fwd[idx] = [int(i), 0]
                            else:
                                config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                config_dict_scaleout['num_pvc']= no_socket_list[j]
                                config_dict_scaleout['num_tiles_per_pvc']=tile_per_socket_list[j]
                                compute = Comms_scaleout(config_dict_scaleout)
                                out = compute.scaleout()
                                config_dict_scaleout['num_pvc'] = total_nu_cards
                                config_dict_scaleout['num_tiles_per_pvc'] = nu_tiles
                                if algo_list[j] == "allreduce":
                                    scaleout_time_fwd[idx]=[int(i), multiply_factor_scaleout*out/1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_fwd[idx]=[int(i), multiply_factor_scaleout*out/(2*1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_fwd[idx]=[int(i), 0]

                        elif  msg_pass_type_list[j] == 'INP_GRAD':
                            if int(no_socket_list[j]) <= int(config_dict_scaleout['num_PVC_per_host']):
                                #config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                scaleout_time_inp[idx] = [int(i), 0]
                            else:
                                config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                config_dict_scaleout['num_pvc'] = no_socket_list[j]
                                config_dict_scaleout['num_tiles_per_pvc'] = tile_per_socket_list[j]
                                compute = Comms_scaleout(config_dict_scaleout)
                                out = compute.scaleout()
                                config_dict_scaleout['num_pvc'] = total_nu_cards
                                config_dict_scaleout['num_tiles_per_pvc'] = nu_tiles
                                if algo_list[j] == "allreduce":
                                    scaleout_time_inp[idx]=[int(i), multiply_factor_scaleout*out/1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_inp[idx]=[int(i), multiply_factor_scaleout*out/(2*1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_inp[idx]=[int(i), 0]

                        elif msg_pass_type_list[j] == 'WT_GRAD':
                            if int(no_socket_list[j]) == 0:
                                num_cards_for_wgt_grad = math.floor(int(total_nu_cards)/(model_split/int(config_dict_scaleout['num_tiles_per_pvc'])))
                                #print(num_cards_for_wgt_grad)
                                config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                config_dict_scaleout['num_pvc'] = num_cards_for_wgt_grad
                                config_dict_scaleout['num_tiles_per_pvc'] = 1
                                config_dict_scaleout['num_PVC_per_host'] = 1
                                compute = Comms_scaleout(config_dict_scaleout)
                                out = compute.scaleout()
                                config_dict_scaleout['num_pvc'] = total_nu_cards
                                config_dict_scaleout['num_tiles_per_pvc'] = nu_tiles
                                config_dict_scaleout['num_PVC_per_host'] = nu_cards
                                if algo_list[j] == "allreduce":
                                    scaleout_time_wt[idx]=[int(i), multiply_factor_scaleout*out/1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_wt[idx]=[int(i), multiply_factor_scaleout*out/(2*1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_wt[idx]=[int(i), 0]
                            else:
                                num_cards_for_wgt_grad = math.floor(int(total_nu_cards)/(model_split/int(config_dict_scaleout['num_tiles_per_pvc'])))
                                config_dict_scaleout['scale_out_msg_size'] = msg_size_list[j]
                                config_dict_scaleout['num_pvc'] = num_cards_for_wgt_grad
                                config_dict_scaleout['num_tiles_per_pvc'] = 1
                                config_dict_scaleout['num_PVC_per_host'] = math.floor(nu_cards/(model_split/int(config_dict_scaleout['num_tiles_per_pvc'])))
                                compute = Comms_scaleout(config_dict_scaleout)
                                out = compute.scaleout()
                                config_dict_scaleout['num_pvc'] = total_nu_cards
                                config_dict_scaleout['num_tiles_per_pvc'] = nu_tiles
                                config_dict_scaleout['num_PVC_per_host'] = nu_cards
                                if algo_list[j] == "allreduce":
                                    scaleout_time_wt[idx]=[int(i), multiply_factor_scaleout*out/1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_wt[idx]=[int(i), multiply_factor_scaleout*out/(2*1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_wt[idx]=[int(i), 0]

                    scaleout_time[idx] = [int(i),1]#[int(i), multiply_factor_scaleout * out / 1000]

    else:
        scaleout_time_fwd = [[]] * len(unique_layer_ID)
        scaleout_time_inp = [[]] * len(unique_layer_ID)
        scaleout_time_wt = [[]] * len(unique_layer_ID)
        for i in unique_layer_ID:
            idx = np.asscalar(np.where(unique_layer_ID == i)[0])
            for j in range(0, len(msg_size_list)):
                if i == layer_ID_list[j]:
                    scaleout_time_fwd[idx] = [int(i), 0]
                    scaleout_time_inp[idx] = [int(i), 0]
                    scaleout_time_wt[idx] = [int(i), 0]
    #print(np.asarray(scaleout_time))


    #-----------------------------------------------------------------------------------------------------------------------


    # with open("out1.csv", "w", newline="") as f:
    #      writer = csv.writer(f)
    #      writer.writerows(final_time)

    #print(len(final_time))
    #print(len(compute_time))
    #print(final_time)
    final_time = np.asarray(final_time)
    compute_time = np.asarray(compute_time)
    dummy_a = (np.where(compute_time[:,2]==0))
    dummy_b = (np.where(compute_time[:,3] == 0))
    non_comms_layer_index = np.intersect1d(dummy_a,dummy_b)
    dummy_c = (np.where(compute_time[:,2]!=0))
    dummy_d = (np.where(compute_time[:,3] != 0))
    comms_layer_index = np.union1d(dummy_c,dummy_d)
    final_time_x,final_time_y =final_time.shape
    compute_time_x,compute_time_y =compute_time.shape
    comute_time_no_IP_wt_GRAD = np.zeros((len(non_comms_layer_index), compute_time_y))
    comute_time_with_IP_or_wt_GRAD = np.zeros((len(comms_layer_index), compute_time_y))
    comms_time_with_IP_or_wt_GRAD = np.zeros((len(comms_layer_index), final_time_y))
    for i in range(len(non_comms_layer_index)):
         comute_time_no_IP_wt_GRAD[i] = compute_time[non_comms_layer_index[i]]
    #print(comute_time_no_IP_wt_GRAD)
    for i in range(len(comms_layer_index)):
         comute_time_with_IP_or_wt_GRAD[i] = compute_time[comms_layer_index[i]]
         comms_time_with_IP_or_wt_GRAD[i] = final_time[comms_layer_index[i]]
    #print(comute_time_with_IP_or_wt_GRAD)
    #print(comms_time_with_IP_or_wt_GRAD)
    final_time=comms_time_with_IP_or_wt_GRAD.tolist()
    compute_time=comute_time_with_IP_or_wt_GRAD.tolist()
    total_comute_time_no_IP_wt_GRAD = sum(comute_time_no_IP_wt_GRAD[:,1])
    #print(total_comute_time_no_IP_wt_GRAD)
    # print(int(max(np.asarray(compute_time)[:,0])))
    # print(int(min(np.asarray(compute_time)[:,0])))

    compute_comms_time = combine_compute_comms(final_time,compute_time)

    #--------------------------Combining scaleout time and scaleup time-------------------------------------
    # compute_comms_time = np.asarray(compute_comms_time)
    # scaleout_layer_index= np.in1d(np.asarray(scaleout_time)[:,0], compute_comms_time[:,0]).nonzero()[0]
    # valid_scaleout_time = np.asarray(np.asarray(scaleout_time)[scaleout_layer_index,1])
    # valid_scaleout_time = np.reshape(valid_scaleout_time,(valid_scaleout_time.shape[0],1))
    # compute_comms_time_with_scaleout = np.concatenate((compute_comms_time, valid_scaleout_time), axis=1)
    # compute_comms_time = compute_comms_time_with_scaleout


    #--------------------------------------------------------------------------------------------------------


    with open(output_file_path, "w") as f:  #, newline=""
        writer = csv.writer(f,delimiter=',')
        writer.writerow(['Layer','Fwd_time(msec)','bwd_time(msec)','wt_grad_time(msec)','comms_time_fwd',
                                'comms_time_inp_grad','comms_time_wtgrad','Total_comms_time(without overlap)',
                                'Total comms_time_with_overlap(wtgrad)','Total comms_time_with_overlap(INPGRAD)',
                                'total_compute_time_without_comms','msg_size'])#,'scaleout time (ms)'])
        writer.writerows(compute_comms_time)

    #_____________________________________JSON-start___________________________________________
    layer_number = np.asarray(compute_comms_time)[:,0]
    # print(scaleout_time_fwd)
    # print("HI")
    # print(layer_number)
    comms_time_fwd = np.asarray(compute_comms_time)[:,4]
    comms_time_inp_grad = np.asarray(compute_comms_time)[:,5]
    comms_time_wtgrad = np.asarray(compute_comms_time)[:,6]
    comms_scaleout = np.asarray(compute_comms_time)[:,12]
    import json
    with open(workload_graph) as fin:
        netinfo = json.load(fin)
    # for i in netinfo['layers']:
    #     i['comms_time_fwd_ms'] = 0.0
    #     i['comms_time_inp_grad_ms'] = 0.0
    #     i['comms_time_wtgrad_ms'] = 0.0
    #     for index in layer_number:
    #            if (i['Layer Idx']+1) == index:
    #                index_location = np.where(layer_number == index)
    #                #print(i['Layer Idx']+1)
    #                #print(np.asscalar(comms_time_fwd[index_location]))
    #                i['comms_time_fwd_ms'] = np.asscalar(comms_time_fwd[index_location])
    #                i['comms_time_inp_grad_ms'] = np.asscalar(comms_time_inp_grad[index_location])
    #                i['comms_time_wtgrad_ms'] = np.asscalar(comms_time_wtgrad[index_location])

    frequency_Ghz = float(config_dict["frequency_in_Ghz"])
    for i in netinfo['nodes']:
        i['data']['Layer']['comms_time_fwd_cycles'] = 0.0
        i['data']['Layer']['comms_time_inp_grad_cycles'] = 0.0
        i['data']['Layer']['comms_time_wtgrad_cycles'] = 0.0
        i['data']['Layer']['comms_time_scaleout_cycles'] = 0.0
        for index in layer_number:
               if (i['data']['Layer']['Layer Index']+1) == index:
                   index_location = np.where(layer_number == index)
                   #print(index_location)
                   #print(i['Layer Idx']+1)
                   #print(np.asscalar(comms_time_fwd[index_location]))
                   i['data']['Layer']['comms_time_fwd_cycles'] = np.asscalar(comms_time_fwd[index_location])*(1000000000*frequency_Ghz)/1000
                   i['data']['Layer']['comms_time_inp_grad_cycles'] = np.asscalar(comms_time_inp_grad[index_location])*(1000000000*frequency_Ghz)/1000
                   i['data']['Layer']['comms_time_wtgrad_cycles'] = np.asscalar(comms_time_wtgrad[index_location])*(1000000000*frequency_Ghz)/1000
                   i['data']['Layer']['comms_time_scaleout_cycles'] = np.asscalar(comms_scaleout[index_location])*(1000000000*frequency_Ghz)/1000



    with open(workload_graph, 'w') as f:
        json.dump(netinfo, f,indent=4)
    #_____________________________________JSON-end___________________________________________

    a=calc_time_and_effic(compute_comms_time,total_comute_time_no_IP_wt_GRAD)
    #print(a)

    with open(output_file_path, mode='a') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        output_writer.writerow(['------------------------------------------------------------------------------------------'])
        output_writer.writerow(['Comms_time','total_compute_time_with_comms(full_overlpa)','total_compute_time_without_comms',
                                'Scaling_Efficiency (full overlap)','Total_compute+comms_without_overlap','Scaling_efficiency',
                                'Total_comms_with_relastic_overlap only w_grad_','Scaling_efficiency'])
        output_writer.writerow(a)



    no_of_cards = int(config_dict["no_of_cards"])
    no_of_tiles_card = int(config_dict["no_of_tiles_card"])
    batch_size = int(config_dict["batch_size"])
    Throughput_full_overlap= 1000*batch_size/a[1] #*no_of_cards*no_of_tiles_card
    Throughput_no_overlap=1000*batch_size/a[4] #*no_of_cards*no_of_tiles_card
    Throughput_realistic_overlap=1000*batch_size/a[6] #*no_of_cards*no_of_tiles_card
    # print("                       ")
    # print("-----------------------------------------------------")
    # print("For detailed report, Please open Report.csv")
    # print('Throughput_full_overlap:',Throughput_full_overlap)
    # print('Throughput_no_overlap:',Throughput_no_overlap)
    # #print('Throughput_realistic_overlap:',Throughput_realistic_overlap)
    # print("-----------------------------------------------------")
    # print("                       ")
    with open(output_file_path, mode='a') as output_file:
        output_writer = csv.writer(output_file, delimiter=',')
        output_writer.writerow(['------------------------------------------------------------------------------------------'])
        output_writer.writerow(['Throughput_full_overlap:',Throughput_full_overlap])
        output_writer.writerow(['Throughput_no_overlap:',Throughput_no_overlap])
