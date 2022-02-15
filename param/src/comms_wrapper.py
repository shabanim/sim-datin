import csv
import numpy as np
import math
import pandas
from .stats import CommsStats
from .multidispatch import comms
from .ring import comms
from .p2p import comms
from .bidir_ring import comms
from .hypercube import comms
from .torus3d import comms
from .utils_param import COLUMNS
from .flat import comms_scaleout
from .pod import comms_scaleout
from .fat_tree import comms_scaleout
from .factory_comms import get_network_collective
from .comms import combine_compute_comms_no_overlap
from .utils_param import _get_xe_link_BW_for_switch_scaleout, add_checkpoint_info_into_json
from .zero import zero, get_collective_comms_type
from .cpu_gpu import zero_cpu_gpu_comms


def comms_wrapper(knobs, comms_csv, compute_csv, output_file_path, workload_graph):
    model_split = knobs['model_split'] if not knobs['data_parallel'] else 1


    comms_df = pandas.read_csv(comms_csv)
    msg_size_list = comms_df[COLUMNS.msg_size].tolist()
    algo_list = comms_df[COLUMNS.algo].tolist()
    no_socket_list = comms_df[COLUMNS.no_of_gpu].tolist()
    tile_per_socket_list = comms_df[COLUMNS.no_of_tile].tolist()
    msg_pass_type_list = comms_df[COLUMNS.pass_type].tolist()
    layer_ID_list = comms_df[COLUMNS.layer_id].tolist()

    # no header present in compute csv
    compute_df = pandas.read_csv(compute_csv, header=None)
    compute_df.columns = [COLUMNS.layer_id, COLUMNS.fwd_time, COLUMNS.bwd_time, COLUMNS.wt_time]
    compute_layer_id_list = compute_df[COLUMNS.layer_id].tolist()
    compute_fwd_time_list = compute_df[COLUMNS.fwd_time].tolist()
    compute_bwd_time_list = compute_df[COLUMNS.bwd_time].tolist()
    compute_wt_grad_time_list = compute_df[COLUMNS.wt_time].tolist()

    compute_time = [[]] * len(compute_layer_id_list)
    for i in range(len(compute_layer_id_list)):
        compute_time[i] = [int(float(compute_layer_id_list[i])),
                           float(compute_fwd_time_list[i]),
                           float(compute_bwd_time_list[i]),
                           float(compute_wt_grad_time_list[i])]
        # print(compute_time[i])

    Final_Total_time_us_list = []  # *len(msg_size_list)

    # For testing
    with open("scaleup.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["msg_size", "no_socket", "tile_per_socket", "algo_list", "layer_ID_list", "msg_pass_type_list"])

    msg_size_list, algo_list, msg_pass_type_list = zero(knobs, workload_graph, layer_ID_list,
                                                        msg_size_list, algo_list, msg_pass_type_list)

    for i in range(len(msg_size_list)):
        # print (data_parallel)
        if knobs["data_parallel"]:
            coms_input_dict = {"msg_size": msg_size_list[i],
                               "no_socket": no_socket_list[i],
                               "tile_per_socket": tile_per_socket_list[i],
                               }
        else:
            if int(no_socket_list[i]) >= int(knobs["num_PVC_per_host"]):
                coms_input_dict = {"msg_size": msg_size_list[i],
                                   "no_socket": knobs["num_PVC_per_host"],
                                   "tile_per_socket": tile_per_socket_list[i],
                                   }
            else:
                if msg_pass_type_list[i]=="FWD" or msg_pass_type_list[i]=="INP_GRAD" :
                    coms_input_dict = {"msg_size": msg_size_list[i],
                                       "no_socket": no_socket_list[i],
                                       "tile_per_socket": tile_per_socket_list[i],
                                       }
                else:
                    coms_input_dict = {"msg_size": msg_size_list[i],
                                       "no_socket": no_socket_list[i],
                                       "tile_per_socket": tile_per_socket_list[i],
                                       }

        if algo_list[i] != '0' and  \
                float(coms_input_dict["msg_size"]) > 0 and \
                float(coms_input_dict["no_socket"]):

            network, collective = get_network_collective(knobs,
                                                         knobs.collective_knobs["scale_up_collectiveAlgo"]["nw_topology"],
                                                         algo_list[i])
            stats = comms(network, collective,
                              float(coms_input_dict["msg_size"]),
                              float(coms_input_dict["tile_per_socket"]),
                              float(coms_input_dict["no_socket"]))
        else:
            stats = CommsStats()
        # For testing
        temp = [coms_input_dict["msg_size"], coms_input_dict["no_socket"], coms_input_dict["tile_per_socket"],
                algo_list[i], layer_ID_list[i], msg_pass_type_list[i]]
        with open("scaleup.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(temp)


        # print(out)
        multiply_factor = 1 + float(knobs["su_jitter"])
        if knobs["so_enabled"]:
            if knobs['so_hw_type'] == '3':
                Final_Total_time_us_list.append(multiply_factor * stats.mdfi_time_us)
            else:
                Final_Total_time_us_list.append(multiply_factor * stats.total_time_us)
        else:
            Final_Total_time_us_list.append(multiply_factor * stats.total_time_us)

    layer_ID_list = list(map(float, layer_ID_list))
    layer_ID_list = list(map(int, layer_ID_list))
    unique_layer_ID = np.unique(np.array(layer_ID_list))
    # print(unique_layer_ID)
    # print(['Layer ID','FWD','INP_GRAD','WT_GRAD'])
    final_time = [[]] * len(unique_layer_ID)
    for i in unique_layer_ID:
        idx = np.asscalar(np.where(unique_layer_ID == i)[0])
        sum_FWD = 0.0
        sum_INP_GRAD = 0.0
        sum_WT_GRAD = 0.0
        sum_WT = 0.0
        for j in range(0, len(msg_size_list)):
            if i == layer_ID_list[j]:
                if msg_pass_type_list[j] == 'FWD':
                    sum_FWD = sum_FWD + float(Final_Total_time_us_list[j])
                elif msg_pass_type_list[j] == 'INP_GRAD':
                    sum_INP_GRAD = sum_INP_GRAD + float(Final_Total_time_us_list[j])
                elif msg_pass_type_list[j] == 'WT_GRAD':
                    sum_WT_GRAD = sum_WT_GRAD + float(Final_Total_time_us_list[j])

                sum_WT = sum_WT + float(msg_size_list[j])
        sum_FWD = sum_FWD / 1000
        sum_INP_GRAD = sum_INP_GRAD / 1000
        sum_WT_GRAD = sum_WT_GRAD / 1000
        final_time[idx] = [i, sum_FWD, sum_INP_GRAD, sum_WT_GRAD, sum_WT]
        # print(final_time[idx])

    # --------------------------------------------------Scaleout-------------------------------------------------------------

    if knobs["so_enabled"]:
        multiply_factor_scaleout = 1 + knobs["so_jitter"]
        if knobs["data_parallel"]:
            scaleout_time_fwd = [[]] * len(unique_layer_ID)
            scaleout_time_inp = [[]] * len(unique_layer_ID)
            scaleout_time_wt = [[]] * len(unique_layer_ID)
            scaleout_time = [[]] * len(unique_layer_ID)

            # For testing
            with open("scaleout.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["msg_size", "no_socket", "tile_per_socket", "algo_list", "layer_ID_list", "msg_pass_type_list",
                     "scaleout cards"])
            # --

            for i in unique_layer_ID:
                knobs._network_knobs['total_Xe_bw_GBps'] = _get_xe_link_BW_for_switch_scaleout(knobs)
                idx = np.asscalar(np.where(unique_layer_ID == i)[0])
                out = 0
                # print(idx)
                for j in range(0, len(msg_size_list)):
                    if i == layer_ID_list[j]:
                        scaleout_time_fwd[idx] = [int(i), 0,0]
                        scaleout_time_inp[idx] = [int(i), 0,0]
                        scaleout_time_wt[idx] = [int(i), 0,0]
                        if msg_pass_type_list[j] == 'WT_GRAD':
                            network, collective = get_network_collective(knobs,
                                                                         knobs.collective_knobs[
                                                                             "scale_out_collectiveAlgo"]["nw_topology"],
                                                                         knobs.collective_knobs[
                                                                             "scale_out_collectiveAlgo"]["collective_algo"])
                            out1,out2 = comms_scaleout(network, collective, float(msg_size_list[j]))
                            scaleout_time[idx] = [int(i), multiply_factor_scaleout * out1 / 1000,multiply_factor_scaleout * out2 / 1000]
                            scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / 1000, multiply_factor_scaleout * out2 / 1000]
                            temp = [msg_size_list[j], knobs['num_PVC_per_host'],
                                    knobs['num_tiles_per_pvc'],
                                    algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                    knobs['num_pvc']]
                        elif msg_pass_type_list[j] == 'FWD':
                            scaleout_time_fwd[idx] = [int(i), 0 ,0]
                            temp = [msg_size_list[j], knobs['num_PVC_per_host'],
                                    knobs['num_tiles_per_pvc'],
                                    algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                    knobs['num_pvc']]
                        elif msg_pass_type_list[j] == 'INP_GRAD':
                            scaleout_time_inp[idx] = [int(i), 0 ,0]
                            temp = [msg_size_list[j], knobs['num_PVC_per_host'],
                                    knobs['num_tiles_per_pvc'],
                                    algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                    knobs['num_pvc']]
                        else:
                            scaleout_time_fwd[idx] = [int(i), 0,0]
                            scaleout_time_inp[idx] = [int(i), 0,0]
                            scaleout_time_wt[idx] = [int(i), 0,0]
                            temp = [msg_size_list[j], knobs['num_PVC_per_host'],
                                    knobs['num_tiles_per_pvc'],
                                    algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                    knobs['num_pvc']]
                            # For testing
                        with open("scaleout.csv", "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(temp)
        else:
            print("Model Parallel")
            knobs._network_knobs['total_Xe_bw_GBps'] = _get_xe_link_BW_for_switch_scaleout(knobs)
            #knobs['num_tiles_per_pvc'] = knobs["no_of_tiles_card"]
            #knobs['num_PVC_per_host'] = knobs["num_PVC_per_host"]
            scaleout_time_fwd = [[]] * len(unique_layer_ID)
            scaleout_time_inp = [[]] * len(unique_layer_ID)
            scaleout_time_wt = [[]] * len(unique_layer_ID)
            scaleout_time = [[]] * len(unique_layer_ID)
            total_nu_cards = int(knobs['num_pvc'])
            nu_tiles = int(knobs['num_tiles_per_pvc'])
            nu_cards = int(knobs["num_PVC_per_host"])

            # For testing
            with open("scaleout.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["msg_size", "no_socket", "tile_per_socket", "algo_list", "layer_ID_list", "msg_pass_type_list",
                     "scaleout cards"])
            # --

            for i in unique_layer_ID:
                idx = np.asscalar(np.where(unique_layer_ID == i)[0])
                out = 0
                scaleout_time_fwd[idx] = [int(i), 0,0]
                scaleout_time_inp[idx] = [int(i), 0,0]
                scaleout_time_wt[idx] = [int(i), 0,0]

                for j in range(0, len(msg_size_list)):
                    if i == layer_ID_list[j]:
                        if msg_pass_type_list[j] == 'FWD':
                            if algo_list[j] == "a2a": # ['a2a', reduce, gather, ]
                                # TODO: Fix below line in refactor 2
                                knobs._network_knobs['so_data_parallel_with_model_split'] = 4
                            else:
                                knobs._network_knobs['so_data_parallel_with_model_split'] = 0

                            if no_socket_list[j] <= knobs['num_PVC_per_host']:
                                # knobs['scale_out_msg_size'] = msg_size_list[j]
                                # For testing
                                temp = [msg_size_list[j], '0',
                                        '0',
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j], '0']
                                # --------
                                scaleout_time_fwd[idx] = [int(i), 0,0]
                            else:
                                # knobs['scale_out_msg_size'] = msg_size_list[j]
                                knobs._network_knobs['num_pvc'] = int(no_socket_list[j])
                                knobs._network_knobs['num_tiles_per_pvc'] = int(tile_per_socket_list[j])
                                network, collective = get_network_collective(knobs,
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "nw_topology"],
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "collective_algo"])
                                out1,out2 = comms_scaleout(network, collective, float(msg_size_list[j]))
                                # For testing
                                temp = [msg_size_list[j], knobs._network_knobs['num_PVC_per_host'],
                                        knobs._network_knobs['num_tiles_per_pvc'],
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                        knobs._network_knobs['num_pvc']]
                                # print(temp)
                                # --------
                                knobs._network_knobs['num_pvc'] = int(total_nu_cards)
                                knobs._network_knobs['num_tiles_per_pvc'] = int(nu_tiles)
                                if algo_list[j] == "allreduce":
                                    scaleout_time_fwd[idx] = [int(i), multiply_factor_scaleout * out1 / 1000, multiply_factor_scaleout * out2 / 1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_fwd[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000), multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "a2a":
                                    scaleout_time_fwd[idx] = [int(i), multiply_factor_scaleout * out1 / (1000),multiply_factor_scaleout * out2 / (1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_fwd[idx] = [int(i), 0,0]
                            # print(temp)

                        elif msg_pass_type_list[j] == 'INP_GRAD':
                            if algo_list[j] == "a2a":
                                # TODO: Fix below line in refactor 2, pass algo type to comms_scaleout to remove  this logic
                                knobs._network_knobs['so_data_parallel_with_model_split'] = 4
                            else:
                                knobs._network_knobs['so_data_parallel_with_model_split'] = 0
                            if no_socket_list[j] <= knobs['num_PVC_per_host']:
                                # knobs['scale_out_msg_size'] = msg_size_list[j]
                                # For testing
                                temp = [msg_size_list[j], '0',
                                        '0',
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j], '0']
                                # --------
                                scaleout_time_inp[idx] = [int(i), 0,0]

                            else:
                                # knobs['scale_out_msg_size'] = msg_size_list[j]
                                knobs._network_knobs['num_pvc'] = int(no_socket_list[j])
                                knobs._network_knobs['num_tiles_per_pvc'] = int(tile_per_socket_list[j])
                                network, collective = get_network_collective(knobs,
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "nw_topology"],
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "collective_algo"])
                                out1,out2 = comms_scaleout(network, collective, float(msg_size_list[j]))
                                # For testing
                                temp = [msg_size_list[j], knobs._network_knobs['num_PVC_per_host'],
                                        knobs._network_knobs['num_tiles_per_pvc'],
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                        knobs._network_knobs['num_pvc']]
                                # --------
                                knobs._network_knobs['num_pvc'] = int(total_nu_cards)
                                knobs._network_knobs['num_tiles_per_pvc'] = int(nu_tiles)

                                # TODO: move into collective
                                if algo_list[j] == "allreduce":
                                    scaleout_time_inp[idx] = [int(i), multiply_factor_scaleout * out1 / 1000, multiply_factor_scaleout * out2 / 1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_inp[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000),multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "a2a":
                                    scaleout_time_inp[idx] = [int(i), multiply_factor_scaleout * out1 / (1000), multiply_factor_scaleout * out2 / (1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_inp[idx] = [int(i), 0,0]
                            # print(temp)

                        elif msg_pass_type_list[j] == 'WT_GRAD':
                            if knobs["hybrid_model"]:
                                if algo_list[j] == "reduce":
                                    # TODO: Fix below line in refactor 2
                                    knobs._network_knobs['so_data_parallel_with_model_split'] = 3
                                else:
                                    knobs._network_knobs['so_data_parallel_with_model_split'] = 2
                            else:
                                if algo_list[j] == "reduce":
                                    # TODO: Fix below line in refactor 2
                                    knobs._network_knobs['so_data_parallel_with_model_split'] = 3
                                else:
                                    if knobs['ZeRO_type'] == 4:
                                        knobs._network_knobs['so_data_parallel_with_model_split'] = 0 #handling zero inf
                                    else:
                                        knobs._network_knobs['so_data_parallel_with_model_split'] = 1


                            if int(no_socket_list[j]) == 0:
                                # num_cards_for_wgt_grad = math.floor(int(total_nu_cards) / (
                                #             model_split / int(knobs['num_tiles_per_pvc'])))

                                num_cards_for_wgt_grad = math.floor(int(total_nu_cards))
                                knobs._network_knobs['num_pvc'] = num_cards_for_wgt_grad #* nu_cards
                                network, collective = get_network_collective(knobs,
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "nw_topology"],
                                                                             knobs.collective_knobs[
                                                                                 "scale_out_collectiveAlgo"][
                                                                                 "collective_algo"])
                                out1,out2 = comms_scaleout(network, collective, float(msg_size_list[j]))
                                # For testing
                                temp = [msg_size_list[j], knobs._network_knobs['num_PVC_per_host'],
                                        knobs._network_knobs['num_tiles_per_pvc'],
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                        float(knobs._network_knobs['num_pvc'] / nu_cards)]
                                # --------
                                knobs._network_knobs['num_pvc'] = total_nu_cards
                                # TODO: move to collective
                                if algo_list[j] == "allreduce":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / 1000, multiply_factor_scaleout * out2 / 1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000), multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "reduce_scatter":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000), multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "reduce":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (1000), multiply_factor_scaleout * out2 / (1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_wt[idx] = [int(i), 0,0]
                            else:

                                if knobs["hybrid_model"]:
                                    network, collective = get_network_collective(knobs,
                                                                                 knobs.collective_knobs[
                                                                                     "scale_out_collectiveAlgo"][
                                                                                     "nw_topology"],
                                                                                 knobs.collective_knobs[
                                                                                     "scale_out_collectiveAlgo"][
                                                                                     "collective_algo"])
                                else:
                                    num_cards_for_wgt_grad = math.floor(int(total_nu_cards) )
                                    #print(int(knobs._network_knobs['num_tiles_per_pvc']))
                                    #knobs._network_knobs['so_msg_size'] = int(msg_size_list[j])
                                    knobs._network_knobs['num_pvc'] = int(num_cards_for_wgt_grad)
                                    # knobs['num_PVC_per_host'] = math.floor(nu_cards/(model_split/int(knobs['num_tiles_per_pvc'])))
                                    # knobs['num_tiles_per_pvc'] = 1
                                    network, collective = get_network_collective(knobs,
                                                                                 knobs.collective_knobs[
                                                                                     "scale_out_collectiveAlgo"][
                                                                                     "nw_topology"],
                                                                                 knobs.collective_knobs[
                                                                                     "scale_out_collectiveAlgo"][
                                                                                     "collective_algo"])
                                out1,out2 = comms_scaleout(network, collective, float(msg_size_list[j]))
                                # For testing
                                temp = [msg_size_list[j], knobs._network_knobs['num_PVC_per_host'],
                                        knobs._network_knobs['num_tiles_per_pvc'],
                                        algo_list[j], layer_ID_list[j], msg_pass_type_list[j],
                                        knobs._network_knobs['num_pvc']]
                                # --------
                                knobs._network_knobs['num_pvc'] = total_nu_cards
                                # knobs['num_tiles_per_pvc'] = nu_tiles
                                # knobs['num_PVC_per_host'] = nu_cards
                                if algo_list[j] == "allreduce":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / 1000, multiply_factor_scaleout * out2 / 1000]
                                elif algo_list[j] == "allgather":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000), multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "reduce_scatter":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (2 * 1000), multiply_factor_scaleout * out2 / (2 * 1000)]
                                elif algo_list[j] == "reduce":
                                    scaleout_time_wt[idx] = [int(i), multiply_factor_scaleout * out1 / (1000), multiply_factor_scaleout * out2 / (1000)]
                                elif algo_list[j] == "0":
                                    scaleout_time_wt[idx] = [int(i), 0,0]

                            # print(temp)
                        else:
                            scaleout_time_wt[idx] = [int(i), 0,0]

                            # For testing
                            temp = [msg_size_list[j], '0',
                                    '0',
                                    algo_list[j], layer_ID_list[j], msg_pass_type_list[j], '0']
                            # --------
                        # print(temp)
                        # For testing
                        with open("scaleout.csv", "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(temp)
                        # # print(temp)
                        # # --


    else:
        scaleout_time_fwd = [[]] * len(unique_layer_ID)
        scaleout_time_inp = [[]] * len(unique_layer_ID)
        scaleout_time_wt = [[]] * len(unique_layer_ID)
        for i in unique_layer_ID:
            idx = np.asscalar(np.where(unique_layer_ID == i)[0])
            for j in range(0, len(msg_size_list)):
                if i == layer_ID_list[j]:
                    scaleout_time_fwd[idx] = [int(i), 0,0]
                    scaleout_time_inp[idx] = [int(i), 0,0]
                    scaleout_time_wt[idx] = [int(i), 0,0]
    # print(np.asarray(scaleout_time_fwd))

    # -----------------------------------------------------------------------------------------------------------------------

    final_time = np.asarray(final_time)
    compute_time = np.asarray(compute_time)
    compute_comms_time = combine_compute_comms_no_overlap(final_time, compute_time)

    # --------------------------------------------------------------------------------------------------------

    with open(output_file_path, "w") as f:  # , newline=""
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['Layer', 'Fwd_time(msec)', 'bwd_time(msec)', 'wt_grad_time(msec)', 'comms_time_fwd',
                         'comms_time_inp_grad', 'comms_time_wtgrad'])  # ,'Total_comms_time(without overlap)',
        # 'Total comms_time_with_overlap(wtgrad)','Total comms_time_with_overlap(INPGRAD)',
        # 'total_compute_time_without_comms','msg_size'])#,'scaleout time (ms)'])
        writer.writerows(compute_comms_time)

    # _____________________________________JSON-start___________________________________________
    layer_number = np.asarray(compute_comms_time)[:, 0]
    comms_time_fwd = np.asarray(compute_comms_time)[:, 4]
    comms_time_inp_grad = np.asarray(compute_comms_time)[:, 5]
    comms_time_wtgrad = np.asarray(compute_comms_time)[:, 6]
    comms_scaleout_time_fwd_pod = np.asarray(scaleout_time_fwd)[:, 1]
    comms_scaleout_time_inp_pod = np.asarray(scaleout_time_inp)[:, 1]
    comms_scaleout_time_wt_pod = np.asarray(scaleout_time_wt)[:, 1]
    comms_scaleout_time_fwd_nic = np.asarray(scaleout_time_fwd)[:, 2]
    comms_scaleout_time_inp_nic = np.asarray(scaleout_time_inp)[:, 2]
    comms_scaleout_time_wt_nic = np.asarray(scaleout_time_wt)[:, 2]
    import json
    #print(workload_graph)
    with open(workload_graph) as fin:
        netinfo = json.load(fin)

    fwd_collective_comms_type, inp_collective_comms_type, wt_collective_comms_type = get_collective_comms_type(
        layer_ID_list,
        algo_list,
        msg_pass_type_list)
    fwd_collective_comms_type = np.asarray(fwd_collective_comms_type)[:, 1]
    inp_collective_comms_type = np.asarray(inp_collective_comms_type)[:, 1]
    wt_collective_comms_type = np.asarray(wt_collective_comms_type)[:, 1]

    frequency_Ghz = float(knobs["frequency_in_Ghz"])
    for i in netinfo['nodes']:
        i['data']['Layer']['comms_time_fwd_cycles'] = 0.0
        i['data']['Layer']['comms_time_inp_grad_cycles'] = 0.0
        i['data']['Layer']['comms_time_wtgrad_cycles'] = 0.0
        i['data']['Layer']['comms_scaleout_time_fwd_cycles_nic'] = 0.0
        i['data']['Layer']['comms_scaleout_time_inp_cycles_nic'] = 0.0
        i['data']['Layer']['comms_scaleout_time_wt_cycles_nic'] = 0.0

        i['data']['Layer']['comms_scaleout_time_fwd_cycles_pod'] = 0.0
        i['data']['Layer']['comms_scaleout_time_inp_cycles_pod'] = 0.0
        i['data']['Layer']['comms_scaleout_time_wt_cycles_pod'] = 0.0
        i['data']['Layer']['fwd_collective_comms_type'] = "0"
        i['data']['Layer']['inp_collective_comms_type'] = "0"
        i['data']['Layer']['wt_collective_comms_type'] = "0"
        for index in layer_number:
            if (i['data']['Layer']['Layer Index'] + 1) == index:
                index_location = np.where(layer_number == index)
                i['data']['Layer']['comms_time_fwd_cycles'] = np.asscalar(comms_time_fwd[index_location]) * (
                        1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_time_inp_grad_cycles'] = np.asscalar(comms_time_inp_grad[index_location]) * (
                        1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_time_wtgrad_cycles'] = np.asscalar(comms_time_wtgrad[index_location]) * (
                        1000000000 * frequency_Ghz) / 1000


                i['data']['Layer']['comms_scaleout_time_fwd_cycles_nic'] = np.asscalar(
                    comms_scaleout_time_fwd_nic[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_inp_cycles_nic'] = np.asscalar(
                    comms_scaleout_time_inp_nic[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_nic'] = np.asscalar(
                    comms_scaleout_time_wt_nic[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_wt_cycles_nic'] = i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_nic']

                i['data']['Layer']['comms_scaleout_time_fwd_cycles_pod'] = np.asscalar(
                    comms_scaleout_time_fwd_pod[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_inp_cycles_pod'] = np.asscalar(
                    comms_scaleout_time_inp_pod[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_pod'] = np.asscalar(
                    comms_scaleout_time_wt_pod[index_location]) * (1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['comms_scaleout_time_wt_cycles_pod'] = i['data']['Layer'][
                    'comms_scaleout_time_wt_grad_cycles_pod']


                i['data']['Layer']['fwd_collective_comms_type'] = np.asscalar(fwd_collective_comms_type[index_location])
                i['data']['Layer']['inp_collective_comms_type'] = np.asscalar(inp_collective_comms_type[index_location])
                i['data']['Layer']['wt_grad_collective_comms_type'] = np.asscalar(wt_collective_comms_type[index_location])

                # i['data']['Layer']['comms_time_scaleout_cycles'] = np.asscalar(comms_scaleout[index_location])*(1000000000*frequency_Ghz)/1000

    netinfo = zero_cpu_gpu_comms(knobs,netinfo)
    
    with open(workload_graph, 'w') as f:
        json.dump(netinfo, f, indent=4)

    # Add check pointing
    if knobs["data_parallel"] == 0:
        start_number = 7
        interval = 25
        add_checkpoint_info_into_json(workload_graph, start_number, interval)
