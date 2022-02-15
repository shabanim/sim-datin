import pandas as pd
import argparse
import json
import numpy as np

class WorkloadGraph:
    def parser(self, argv, main_list, dict1):

        args = self._parse_command_line_args(argv)
        df = pd.read_csv("Intermediate_file.csv")

        jsonfile = open(args.outputjson, 'w')

        Workload = {}
        Workload["directed"] = True
        Workload["multigraph"] = True

        graph_dict = {}
        node_dict = {}
        node_dict["shape"] = "plaintext"
        edge_dict = {}
        edge_dict["dir"] = "forward"

        graph_dict["node"] = node_dict
        graph_dict["edge"] = edge_dict

        Workload["graph"] = graph_dict

        ###MAKING THE NODES FOR THE JSON FILE
        nodes = []
        last_id = 0
        last_id_list = []
        id_value = 0
        for lists in main_list:
            rep_value = dict1[lists[0]]
            for i in range(0, rep_value):
                if (id_value > 0):
                    last_id = id_value
                    last_id_list.append(last_id)
                for key, value in df.iterrows():
                    if (value["Layer Name"] in lists):
                        node = {}
                        node["label"] = value["Layer Name"]
                        node["typedef"] = "Layer"
                        layer = {}
                        data = {}

                        layer["Layer Name"] = value["Layer Name"]
                        layer["Layer Type"] = value["Layer Type"]
                        layer["Layer Index"] = id_value

                        tensors = []
                        for item in ['Input Tensor dims']:
                            list1 = list(value[item].split(","))
                            # print(list1)
                            for items in list1:
                                tensors.append({"Tensor": {"name": items}})
                            layer["Input Tensor Dims"] = tensors

                        tensors = []
                        for item in ['Output Tensor Dims']:
                            list2 = list(value[item].split(","))
                            for items in list2:
                                tensors.append({"Tensor": {"name": items}})
                            layer["Output Tensor Dims"] = tensors

                        layer["l_pass"] = value["Pass"]
                        layer["wt_grad_msg_size"] = value["Weight Size (Ki)"] * 1000
                        layer["fwd_pass_msg_size"] = 0.0
                        layer["inp_grad_msg_size"] = 0.0
                        # rec["Weigh size"]=value[9]
                        layer["fwd_pass_comp_cycles"] = value["Fwd pass cycles"]
                        layer["inp_grad_comp_cycles"] = value["INP Pass cycles"]
                        layer["wt_grad_comp_cycles"] = value["Weight Cycles"]
                        layer["comms_time_fwd_cycles"] = 0.0
                        layer["comms_time_inp_grad_cycles"] = 0.0
                        layer["comms_time_wtgrad_cycles"] = 0.0
                        layer["comms_scaleout_time_fwd_cycles"] = 0.0
                        layer["comms_scaleout_time_inp_cycles"] = 0.0
                        layer["comms_scaleout_time_wt_cycles"] = 0.0
                        layer["fwd_collective_comms_type"] = "0"
                        layer["inp_collective_comms_type"] = "0"
                        layer["wt_collective_comms_type"] = "0"
                        layer["Checkpoint_number"] = "nan"

                        data["Layer"] = layer
                        node["data"] = data
                        node["id"] = id_value

                        id_value += 1
                        nodes.append(node)
        Workload["nodes"] = nodes

        def myconverter(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.float):
                return float(obj)

        links = []
        list_counter = 0
        for lists in main_list:
            rep_value = dict1[lists[0]]
            list_len = len(lists)
            for i in range(0, rep_value):
                if (i == 0):
                    if (lists == main_list[0] or lists == main_list[1]):
                        list_counter = 0
                else:
                    list_counter += list_len
                predcessor_dict = {}
                predcessor = {}
                for idx in range(0, df.shape[0]):
                    layer_id = df["Layer Idx"][idx]
                    output_layers = list(df["Output Tensor Dims"][idx].split(","))
                    for op_layer in output_layers:
                        if op_layer in predcessor.keys():
                            predcessor_dict[op_layer] = layer_id
                        else:
                            predcessor[op_layer] = layer_id

                    # access the predcessor
                    input_layers = list(df["Input Tensor dims"][idx].split(","))

                    # input_layers.remove("encoder_input_tensor(1;1024;1;1)")
                    for ip_layer in input_layers:
                        if (df["Layer Name"][idx] in lists):
                            # links.clear()
                            # print(ip_layer)
                            target = layer_id + list_counter
                            if ip_layer in predcessor.keys():
                                source = predcessor[ip_layer] + list_counter

                                if (source != target):
                                    link = {}
                                    link["label"] = ip_layer
                                    link["akey"] = ip_layer

                                    tensor = {}
                                    tensor["name"] = ip_layer
                                    # tensor["dims"] = list4[0]

                                    tensors = {}
                                    tensors["Tensors"] = tensor
                                    link["data"] = tensors

                                    link["source"] = source
                                    link["target"] = target
                                    link["key"] = ip_layer
                                    links.append(link)
                                    del predcessor[ip_layer]

                                if ip_layer in predcessor_dict.keys():
                                    source = predcessor_dict[ip_layer]
                                    if (source != target):
                                        link = {}
                                        link["label"] = ip_layer
                                        link["akey"] = ip_layer

                                        tensor = {}
                                        tensor["name"] = ip_layer
                                        # tensor["dims"] = list4[0]

                                        tensors = {}
                                        tensors["Tensors"] = tensor
                                        link["data"] = tensors

                                        link["source"] = source
                                        link["target"] = target
                                        link["key"] = ip_layer
                                        links.append(link)
                            else:
                                if ip_layer in predcessor_dict.keys():
                                    source = predcessor_dict[ip_layer]

                                    if (source != target):
                                        link = {}
                                        link["label"] = ip_layer
                                        link["akey"] = ip_layer
                                        tensor = {}
                                        tensor["name"] = ip_layer
                                        # tensor["dims"] = list4[0]

                                        tensors = {}
                                        tensors["Tensors"] = tensor
                                        link["data"] = tensors

                                        link["source"] = source
                                        link["target"] = target
                                        link["key"] = ip_layer
                                        links.append(link)

        ##LINKS FOR THE OPTIMISER
        for node in nodes:
            if (node["data"]["Layer"]["l_pass"] == "upd"):
                layer_id = node["id"]
                last_layer_id = layer_id - 1
                for key, value in df.iterrows():
                    if (value["Pass"] == "upd"):
                        id_value = value["Layer Idx"] - 1
                        tensor_name = df["Output Tensor Dims"][id_value]
                link = {}
                link["label"] = tensor_name
                link["akey"] = tensor_name
                tensor = {}
                tensor["name"] = tensor_name
                # tensor["dims"] = list4[0]

                tensors = {}
                tensors["Tensors"] = tensor
                link["data"] = tensors

                link["source"] = last_layer_id
                link["target"] = layer_id
                link["key"] = tensor_name
                links.append(link)

        ###NEW LINKS TO LINK THE REPEATED PARTS
        new_links = []
        for i in last_id_list:
            new_link = {}
            new_link["label"] = "New Link"
            new_link["source"] = (i - 1)
            new_link["target"] = i
            new_links.append(new_link)

        for dicts in links:
            for new_dicts in new_links:
                if (dicts["source"] == new_dicts["source"] and dicts["target"] == new_dicts["target"]):
                    new_links.remove(new_dicts)

        for link in links:
            source_id = link["source"]
            target_id = link["target"]
            for node in nodes:
                if (node["id"] == source_id and node["data"]["Layer"]["l_pass"] == "fwd"):
                    for node in nodes:
                        if (node["id"] == target_id and node["data"]["Layer"]["l_pass"] == "bwd"):
                            links.remove(link)

        # print(new_links)

        links.sort(key=lambda e: e["source"])

        links.append(new_links)

        Workload["links"] = links

        json.dump(Workload, jsonfile, indent=4, default=myconverter)

        dump = "var graph_data = " + json.dumps(Workload, indent=2, default=myconverter)
        with open(args.outputjson, 'w') as stream:
            stream.writelines(dump)

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser()
        parser.add_argument("inputfile", help="path of input csv file")
        parser.add_argument("outputjson", help="path of output json file")
        parser.add_argument("output_layer_stats", help="path of the output layer_stat file")
        parser.add_argument("output_stats", help="path of the output stats_200mb file")

        args = parser.parse_args(argv)
        return args