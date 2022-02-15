import pandas as pd
import argparse

class Layer_stats:

    def parser(self,argv,main_list,dict1):

        args = self._parse_command_line_args(argv)
        layer_stats=open(args.output_layer_stats,'w')
        df=pd.read_csv("Intermediate_file.csv")
        #Creating the dataframe
        cols = ["Layer Idx", "Layer Name", "Layer Type", "Pass", "Layer Class", "Input Tensor dims",
            "Input Tensor Size (Ki)", "Filter Size", "Stride Size", "Output Tensor Dims", "Output Tensor Size (Ki)",
            "Weight Size (Ki)", "Layer Compute OPS (M)", "Total Size (Ki)", "Input Sparsity", "Output Sparsity",
            "Parameter Sparsity", "Compute Sparsity"]
        new_dataframe = pd.DataFrame(columns=cols)

        dict_list = []
        id_value = 0

        for lists in main_list:
            rep_value = dict1[lists[0]]
            for i in range(0, rep_value):
                for key, value in df.iterrows():
                    if (value["Layer Name"] in lists):
                        new_dataframe = {}
                        new_dataframe["Layer Idx"] = id_value
                        new_dataframe["Layer Name"] = value["Layer Name"]
                        new_dataframe["Layer Type"] = value["Layer Type"]
                        new_dataframe["Pass"] = value["Pass"]
                        new_dataframe["Layer Class"] = value["Layer Class"]
                        new_dataframe["Input Tensor dims"] = value["Input Tensor dims"]
                        new_dataframe["Input Tensor Size (Ki)"] = value["Input Tensor Size (Ki)"]
                        new_dataframe["Filter Size"] = 0
                        new_dataframe["Stride Size"] = 0
                        new_dataframe["Output Tensor Dims"] = value["Output Tensor Dims"]
                        new_dataframe["Output Tensor Size (Ki)"] = value["Output Tensor Size (Ki)"]
                        new_dataframe["Weight Size (Ki)"] = value["Weight Size (Ki)"]
                        new_dataframe["Layer Compute OPS (M)"] = 0
                        new_dataframe["Total Size (Ki)"] = new_dataframe["Input Tensor Size (Ki)"] + new_dataframe[
                            "Output Tensor Size (Ki)"] + new_dataframe["Weight Size (Ki)"]
                        new_dataframe["Input Sparsity"] = 0
                        new_dataframe["Output Sparsity"] = 0
                        new_dataframe["Parameter Sparsity"] = 0
                        new_dataframe["Compute Sparsity"] = 0
                        id_value = id_value + 1
                        dict_list.append(new_dataframe)
        final = pd.DataFrame(dict_list)
        final.to_csv(layer_stats, mode="w", index=False)

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser()
        parser.add_argument("inputfile", help="path of input csv file")
        parser.add_argument("outputjson", help="path of output json file")
        parser.add_argument("output_layer_stats", help="path of the output layer_stat file")
        parser.add_argument("output_stats", help="path of the output stats_200mb file")

        args = parser.parse_args(argv)
        return args