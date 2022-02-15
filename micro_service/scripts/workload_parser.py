import argparse
import pandas as pd
import sys
import os
from parser_output_scripts import WorkloadGraph
from parser_output_scripts import Layer_stats
from parser_output_scripts import StatsFile

def str_to_boolean(s):
    if isinstance(s, bool):
        return s
    if s.lower() in ['true', 't', 'yes', 'y', 'on', 'enable']:
        return True
    elif s.lower() in ['false', 'f', 'no', 'n', 'off', 'disable']:
        return False
    else:
        raise argparse.ArgumentTypeError('expecting boolean value')


class WorkloadParser():
    """
        invoke single instance of dl-modelling over given config files and generate report
    """
    @staticmethod
    def get_command():
        return "workload_parser"

    def __init__(self):
        pass

    def description(self):
        return "this is parser that takes the excel sheet workloads given by the Archbench tool and converts that into the file that can be used by param tool"


    def exec(self, argv):
        """
        Reading the input file that have forward pass and generating the intermediate csv file for creating the backward pass
	    """
        args = self._parse_command_line_args(argv)
        data = pd.read_csv(args.inputfile)

        ##FORWARD PASS
        dict_list = []
        for key, value in data.iterrows():
            if (value["Pass"] != "oth"):
                dict1 = {}
                dict1["Layer Idx"] = value["Layer Idx"]
                dict1["Layer Name"] = value["Layer Name"]
                dict1["Layer Type"] = value["Layer Type"]
                dict1["Pass"] = value["Pass"]
                dict1["Layer Class"] = value["Layer Class"]
                tensors = []
                for item in ['Input Tensor dims']:
                    list1 = list(value[item].split(","))
                    for items in list1:
                        list3 = list(items.split("("))
                        tensors.append(list3[0])
                    dict1["Input Tensor dims"] = ",".join(tensors)
                dict1["Input Tensor Size (Ki)"] = value["Input Tensor Size (Ki)"]
                tensors = []
                for item in ['Output Tensor Dims']:
                    list2 = list(value[item].split(","))
                    for items in list2:
                        list5 = list(items.split("("))
                        tensors.append(list5[0])
                    dict1["Output Tensor Dims"] = ",".join(tensors)
                dict1["Output Tensor Size (Ki)"] = value["Output Tensor Size (Ki)"]
                dict1["Weight Size (Ki)"] = value["Weight Size (Ki)"]
                dict1["Fwd pass cycles"] = value["Fwd pass cycles"]
                dict1["INP Pass cycles"] = 0
                dict1["Weight Cycles"] = 0
                dict1["Repitation"] = value["Repitation"]
                dict_list.append(dict1)
            else:
                break

        ###DATAFRAME FOR FORWARD PASS
        data1 = pd.DataFrame(dict_list)
        len_data = len(data1) + 1

        ###BACKWARD PASS
        dict_list = []
        for key, value in data.iterrows():
            if (value["Pass"] != "oth"):
                dict1 = {}
                dict1["Layer Idx"] = value["Layer Idx"] + len_data
                dict1["Layer Name"] = "bwd_" + value["Layer Name"]
                dict1["Layer Type"] = value["Layer Type"]
                dict1["Pass"] = "bwd"
                dict1["Layer Class"] = value["Layer Class"]
                ip_list = []
                op_list = []
                ip_layer_list = []
                ip_list = value["Input Tensor dims"].split("(")
                op_list = value["Output Tensor Dims"].split("(")
                ip_layer_list.append(op_list[0] + "_grad")
                ip_layer_list.append(ip_list[0])
                dict1["Input Tensor dims"] = ",".join(ip_layer_list)  # op_list[0]+"_grad",ip_list[0]
                dict1["Input Tensor Size (Ki)"] = value["Output Tensor Size (Ki)"]
                dict1["Output Tensor Dims"] = ip_list[0] + "_grad"
                dict1["Output Tensor Size (Ki)"] = value["Input Tensor Size (Ki)"]
                dict1["Weight Size (Ki)"] = value["Weight Size (Ki)"]
                dict1["Fwd pass cycles"] = 0
                dict1["INP Pass cycles"] = value["INP Pass cycles"]
                dict1["Weight Cycles"] = value["Weight Cycles"]
                dict1["Repitation"] = value["Repitation"]
                dict_list.append(dict1)
            else:
                break

        ###DATAFRAME FOR BACKWARD PASS
        data2 = pd.DataFrame(dict_list)
        data3 = data2.loc[::-1].reset_index(drop=True)
        data3["Layer Idx"] = data3["Layer Idx"].values[::-1]

        ###LOSS LAYER
        loss_layer = data.loc[len(data1), :]
        line = pd.DataFrame(loss_layer)
        dataframe = line.transpose()

        dict_list = []
        for key, value in dataframe.iterrows():
            dict1 = {}
            dict1["Layer Idx"] = value["Layer Idx"]
            dict1["Layer Name"] = value["Layer Name"]
            dict1["Layer Type"] = value["Layer Type"]
            dict1["Pass"] = value["Pass"]
            dict1["Layer Class"] = value["Layer Class"]
            tensors = []
            for item in ['Input Tensor dims']:
                list1 = list(value[item].split(","))
                for items in list1:
                    list3 = list(items.split("("))
                    tensors.append(list3[0])
                dict1["Input Tensor dims"] = ",".join(tensors)
            dict1["Input Tensor Size (Ki)"] = value["Input Tensor Size (Ki)"]
            tensors = []
            for item in ['Output Tensor Dims']:
                list2 = list(value[item].split(","))
                for items in list2:
                    list5 = list(items.split("("))
                    tensors.append(list5[0])
                dict1["Output Tensor Dims"] = ",".join(tensors)
            dict1["Output Tensor Size (Ki)"] = value["Output Tensor Size (Ki)"]
            dict1["Weight Size (Ki)"] = value["Weight Size (Ki)"]
            dict1["Fwd pass cycles"] = value["Fwd pass cycles"]
            dict1["INP Pass cycles"] = 0
            dict1["Weight Cycles"] = 0
            dict1["Repitation"] = value["Repitation"]
            dict_list.append(dict1)

        ###DATAFRAME FOR LOSS LAYER
        loss = pd.DataFrame(dict_list)

        ##LAST LAYER
        layer_id = len(data1) + len(data3) + len(loss)
        last_layer = data.loc[(len(data1) + len(loss)):, ]

        dict_list = []
        for key, value in last_layer.iterrows():
            dict1 = {}
            dict1["Layer Idx"] = layer_id
            dict1["Layer Name"] = value["Layer Name"]
            dict1["Layer Type"] = value["Layer Type"]
            dict1["Pass"] = value["Pass"]
            dict1["Layer Class"] = value["Layer Class"]
            tensors = []
            for item in ['Input Tensor dims']:
                list1 = list(value[item].split(","))
                for items in list1:
                    list3 = list(items.split("("))
                    tensors.append(list3[0])
                dict1["Input Tensor dims"] = ",".join(tensors)
            dict1["Input Tensor Size (Ki)"] = value["Input Tensor Size (Ki)"]
            tensors = []
            for item in ['Output Tensor Dims']:
                list2 = list(value[item].split(","))
                for items in list2:
                    list5 = list(items.split("("))
                    tensors.append(list5[0])
                dict1["Output Tensor Dims"] = ",".join(tensors)
            dict1["Output Tensor Size (Ki)"] = value["Output Tensor Size (Ki)"]
            dict1["Weight Size (Ki)"] = value["Weight Size (Ki)"]
            dict1["Fwd pass cycles"] = value["Fwd pass cycles"]
            dict1["INP Pass cycles"] = 0
            dict1["Weight Cycles"] = 0
            dict1["Repitation"] = value["Repitation"]
            dict_list.append(dict1)

        ##DATAFRAME FOR LAST LAYER
        final_layer = pd.DataFrame(dict_list)

        ###APPENDING THE DATAFRAMES
        set1 = data1.append(loss)
        set2 = set1.append(data3)
        final_set = set2.append(final_layer)

        final_set.to_csv(r"Intermediate_file.csv", mode="w", index=False)

    ##########################################################################################################################

    ##READING THE INTERMEDIATE CSV####
        df= pd.read_csv(r"Intermediate_file.csv")

        ####MAKING SET OF LAYERS TO BE REPEATED BASED ON THE REPETITION VALUE
        list1 = []
        dict1 = {}
        main_list = []
        prev = df["Repitation"][0]
        for key, value in df.iterrows():
            if (prev == value["Repitation"]):
                dict1[value["Layer Name"]] = value["Repitation"]
                list1.append(value["Layer Name"])
                # print(list1)

            else:
                main_list.append(list1)
                list1 = []
                dict1[value["Layer Name"]] = value["Repitation"]
                list1.append(value["Layer Name"])
            prev = value["Repitation"]
        main_list.append(list1)
    ###Creating Json file###
        workload_graph = WorkloadGraph()
        workload_graph.parser(sys.argv[1:], main_list, dict1)

    ###CREATING THE LAYER STATS.CSV FILE##
        layer_stats_obj = Layer_stats()
        layer_stats_obj.parser(sys.argv[1:], main_list, dict1)

    ###CREATING THE STATS_200MB CSV FILE
        stats_file_obj = StatsFile()
        stats_file_obj.parser(sys.argv[1:], main_list, dict1)


    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser()
        parser.add_argument("inputfile", help="path of input csv file")
        parser.add_argument("outputjson", help="path of output json file")
        parser.add_argument("output_layer_stats", help="path of the output layer_stat file")
        parser.add_argument("output_stats", help="path of the output stats_200mb file")

        args = parser.parse_args(argv)
        return args

if __name__ == "__main__":
    workload_parser=WorkloadParser()
    workload_parser.exec(sys.argv[1:])
    os.remove(r"Intermediate_file.csv")