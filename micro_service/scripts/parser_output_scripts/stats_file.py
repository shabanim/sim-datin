import pandas as pd
import argparse

class StatsFile:
    def parser(self,argv,main_list,dict1):

        args = self._parse_command_line_args(argv)
        df=pd.read_csv("Intermediate_file.csv")

        stats_file = open(args.output_stats, 'w')
        cols = ["Layer Index", "Layer Name", "Pass", "Fused", "Storage Option", "Cache Size (Mi)",
                "Read Param Transfer (Ki)", "Read Data Transfer (Ki)", "Write Data Transfer (Ki)",
                "Total Data Transfer (Ki)", "CMX Write Data Transfer (Ki)", "Ideal Cycles", "Effective Cycles",
                "Perf Cycles", "Comp Cycles", "Engine Cycles", "Data Cycles", "Cache Cycles", "Activation Cycles",
                "Parameter Cycles", "Layer Bound", "Total MEM RD/WR BW per Sec (G)",
                "Activation MEM RD/WR BW per Sec (G)",
                "Activation MEM RD BW per Sec (G)", "Activation MEM WR BW per Sec (G)", "Param MEM RD BW per Sec (G)",
                "Total CACHE RD/WR Bytes Transferred", "Total CACHE RD Bytes Transferred",
                "Total CACHE WR Bytes Transferred", "Total L1 RD/WR Bytes Transferred", "Total L1 RD Bytes Transferred",
                "Total L1 WR Bytes Transferred", "Total SLM RD/WR Bytes Transferred", "Total SLM RD Bytes Transferred",
                "Total SLM WR Bytes Transferred", "HW Efficiency (%)", "HW Utilization (%)", "Tile",
                "Tiling Efficiency (%)", "Bound by device", "Mem occupied (Ki)"]

        new_dataframe = pd.DataFrame(columns=cols)

        dict_list = []
        id_value = 0
        for lists in main_list:
            rep_value = dict1[lists[0]]
            for i in range(0, rep_value):
                for key, value in df.iterrows():
                    if (value["Layer Name"] in lists):
                        if (value["Pass"] != "bwd"):
                            new_dataframe = {}
                            new_dataframe["Layer Index"] = id_value
                            new_dataframe["Layer Name"] = value["Layer Name"]
                            new_dataframe["Pass"] = value["Pass"]
                            new_dataframe["Fused"] = "N/A"
                            new_dataframe["Storage Option"] = "FSPC"
                            new_dataframe["Cache Size (Mi)"] = 0
                            new_dataframe["Read Param Transfer (Ki)"] = 0
                            new_dataframe["Read Data Transfer (Ki)"] = 0
                            new_dataframe["Write Data Transfer (Ki)"] = 0
                            new_dataframe["Total Data Transfer (Ki)"] = 0
                            new_dataframe["CMX Write Data Transfer (Ki)"] = 0
                            new_dataframe["Ideal Cycles"] = 0
                            new_dataframe["Effective Cycles"] = 0
                            new_dataframe["Perf Cycles"] = value["Fwd pass cycles"]
                            new_dataframe["Comp Cycles"] = 0
                            new_dataframe["Engine Cycles"] = 0
                            new_dataframe["Data Cycles"] = 0
                            new_dataframe["Cache Cycles"] = 0
                            new_dataframe["Activation Cycles"] = 0
                            new_dataframe["Parameter Cycles"] = 0
                            new_dataframe["Layer Bound"] = 0
                            new_dataframe["Total MEM RD/WR BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM RD/WR BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM RD BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM WR BW per Sec (G)"] = 0
                            new_dataframe["Param MEM RD BW per Sec (G)"] = 0
                            new_dataframe["Total CACHE RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total CACHE RD Bytes Transferred"] = 0
                            new_dataframe["Total CACHE WR Bytes Transferred"] = 0
                            new_dataframe["Total L1 RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total L1 RD Bytes Transferred"] = 0
                            new_dataframe["Total L1 WR Bytes Transferred"] = 0
                            new_dataframe["Total SLM RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total SLM RD Bytes Transferred"] = 0
                            new_dataframe["Total SLM WR Bytes Transferred"] = 0
                            new_dataframe["HW Efficiency (%)"] = 0
                            new_dataframe["HW Utilization (%)"] = 0
                            new_dataframe["Tile"] = 0
                            new_dataframe["Tiling Efficiency (%)"] = 0
                            new_dataframe["Bound by device"] = 0
                            new_dataframe["Mem occupied (Ki)"] = 0
                            id_value = id_value + 1
                            dict_list.append(new_dataframe)
                        else:
                            new_dataframe = {}
                            new_dataframe["Layer Index"] = id_value
                            new_dataframe["Layer Name"] = value["Layer Name"]
                            new_dataframe["Pass"] = "bwd"
                            new_dataframe["Fused"] = "N/A"
                            new_dataframe["Storage Option"] = "FSPC"
                            new_dataframe["Cache Size (Mi)"] = 0
                            new_dataframe["Read Param Transfer (Ki)"] = 0
                            new_dataframe["Read Data Transfer (Ki)"] = 0
                            new_dataframe["Write Data Transfer (Ki)"] = 0
                            new_dataframe["Total Data Transfer (Ki)"] = 0
                            new_dataframe["CMX Write Data Transfer (Ki)"] = 0
                            new_dataframe["Ideal Cycles"] = 0
                            new_dataframe["Effective Cycles"] = 0
                            new_dataframe["Perf Cycles"] = value["INP Pass cycles"] + value["Weight Cycles"]
                            new_dataframe["Comp Cycles"] = 0
                            new_dataframe["Engine Cycles"] = 0
                            new_dataframe["Data Cycles"] = 0
                            new_dataframe["Cache Cycles"] = 0
                            new_dataframe["Activation Cycles"] = 0
                            new_dataframe["Parameter Cycles"] = 0
                            new_dataframe["Layer Bound"] = 0
                            new_dataframe["Total MEM RD/WR BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM RD/WR BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM RD BW per Sec (G)"] = 0
                            new_dataframe["Activation MEM WR BW per Sec (G)"] = 0
                            new_dataframe["Param MEM RD BW per Sec (G)"] = 0
                            new_dataframe["Total CACHE RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total CACHE RD Bytes Transferred"] = 0
                            new_dataframe["Total CACHE WR Bytes Transferred"] = 0
                            new_dataframe["Total L1 RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total L1 RD Bytes Transferred"] = 0
                            new_dataframe["Total L1 WR Bytes Transferred"] = 0
                            new_dataframe["Total SLM RD/WR Bytes Transferred"] = 0
                            new_dataframe["Total SLM RD Bytes Transferred"] = 0
                            new_dataframe["Total SLM WR Bytes Transferred"] = 0
                            new_dataframe["HW Efficiency (%)"] = 0
                            new_dataframe["HW Utilization (%)"] = 0
                            new_dataframe["Tile"] = 0
                            new_dataframe["Tiling Efficiency (%)"] = 0
                            new_dataframe["Bound by device"] = 0
                            new_dataframe["Mem occupied (Ki)"] = 0
                            id_value = id_value + 1
                            dict_list.append(new_dataframe)

        final = pd.DataFrame(dict_list)

        final.to_csv(stats_file, mode="w", index=False)

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser()
        parser.add_argument("inputfile", help="path of input csv file")
        parser.add_argument("outputjson", help="path of output json file")
        parser.add_argument("output_layer_stats", help="path of the output layer_stat file")
        parser.add_argument("output_stats", help="path of the output stats_200mb file")

        args = parser.parse_args(argv)
        return args
