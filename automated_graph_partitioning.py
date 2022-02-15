import os
import sys
import ntpath
import subprocess
import pandas as pd
import argparse

from micro_service.scripts.graph_partitioning import MemoryFootprint

#class planner_algorithm:
def automated_graph_partitioning(argv):


    memory_dict={}
    throughput_list=[]

    args = _parse_command_line_args(argv)

    layerstat=archbench_run(sys.argv[1:])

    stage_list=["Baseline_GB","Zero_stage_1_GB","Zero_stage_2_GB"]
    mp=1024

    while (mp>1):
        print(mp)
        dp = 1024 / mp
        memory_dict = MemoryFootprint.memory_footprint(layerstat, dp, mp)
        peak_memory = 64
        effective_memory=0.6*peak_memory
        for stages in stage_list:
            if (memory_dict[stages] < effective_memory):
                if (stages=="Baseline_GB"):
                    BS_mp = mp
                    BS_dp = dp
                elif(stages=="Zero_stage_1_GB"):
                    Z1_mp = mp
                    Z1_dp = dp
                elif(stages=="Zero_stage_2_GB"):
                    Z2_mp = mp
                    Z2_dp = dp
        mp = mp / 2

    for stages in stage_list:
        if (stages == "Baseline_GB"):
            zero_stage_num = 0
            mp = BS_mp
            dp=BS_dp
        elif (stages == "Zero_stage_1_GB"):
            zero_stage_num = 1
            mp = Z1_mp
            dp = Z1_dp
        elif (stages == "Zero_stage_2_GB"):
            zero_stage_num = 2
            mp = Z2_mp
            dp = Z2_dp

        change_cgf(mp,zero_stage_num,args.configfile)

        change_network_file(mp, args.network_file)

        dl_modeling_flow(args.network_file,args.configfile,args.config_file,args.outputfile)

        new_dataframe = {}
        new_dataframe=get_throughput(mp,dp,stages)
        throughput_list.append(new_dataframe)

    data =pd.DataFrame(throughput_list)
    print(data)
    # #data.to_csv()

def archbench_run(argv):
    args = _parse_command_line_args(argv)
    change_cgf(1,0,args.configfile)
    change_network_file(1,args.network_file)
    dl_modeling_flow(args.network_file,args.configfile,args.config_file,args.outputfile)

    workload_graph = ntpath.basename(args.network_file)
    config_name = ntpath.basename(args.config_file)
    layerstat = "./results/results-{}/{}/{}_layer_stat.csv".format(os.path.splitext(config_name)[0], workload_graph,workload_graph)
    #print(layerstat)
    return layerstat

def change_cgf(mp,zero_stage_num,config_file):

    fin=open(config_file,"r+")
    #fin = open(r"test/data/175B_transformer/base_param_cfg.yml", 'r+')
    str1 = ""
    for lines in fin.readlines():

        list1 = []
        if (lines.strip().startswith("model_split")):
            list1 = lines.split(":")
            str_replace = " " + str(mp)
            lines = lines.replace(list1[1], str_replace)
            str1 += lines + "\n"
        elif(lines.strip().startswith("ZeRO_type")):
            list1 = lines.split(":")
            str_replace = " " + str(zero_stage_num)+" #TODO"
            lines = lines.replace(list1[1], str_replace)
            str1 += lines
        else:
            str1 += lines
    fin.close()
    #with open(r"test/data/175B_transformer/base_param_cfg.yml", 'w') as fp:
    with open(config_file,'w') as fp:
        fp.write(str1)
        fp.close()
    #print(str1)


def change_network_file(mp, network_file):
    str1 = ""
    fin = open(network_file, 'r+')
    #fin = open(r"test/data/175B_transformer/TransformerLanguageModel_175B.py", 'r+')
    for lines in fin.readlines():
        if (lines.strip().startswith("head_divide")):
            list1 = []
            list2 = []
            list1 = lines.split("=")
            list2 = list1[1].split(",")
            lines = lines.replace(list2[0], str(mp))
            str1 += lines
        elif (lines.strip().startswith("d_ff_divide")):
            list1 = []
            list2 = []
            list1 = lines.split("=")
            list2 = list1[1].split(",")
            lines = lines.replace(list2[0], str(mp))
            str1 += lines
        elif (lines.strip().startswith("vocab_divide")):
            list1 = []
            list2 = []
            list1 = lines.split("=")
            list2 = list1[1].split(",")
            lines = lines.replace(list2[0], str(mp))
            str1 += lines
        else:
            str1 += lines
    fin.close()
    with open(network_file, 'w') as fp:
    #with open(r"test/data/175B_transformer/TransformerLanguageModel_175B.py", 'w') as fp:
        fp.write(str1)
        fp.close()

    #print(str1)

def dl_modeling_flow(network_file,configfile,config_file,outputfile):
    cmd = [
        'python', './micro_service/dl-modelling.py', 'summary',
        '-f', network_file,
        '-cf', config_file,
        '-c', configfile,
        '-o', outputfile,
        '--training', '--trg-greedy-flush', 'True', '--trg-optimizer', 'adam', '--dump_html'
    ]
    subprocess.check_call(cmd)

def get_throughput(mp,dp,stages):
    throughput=0
    #html_tables = pd.read_html(speedsim_analysis_file)
    html_tables = pd.read_html(r"modelzoo/SpeedSimAnalysis.html")
    df = html_tables[1]
    for key, value in df.iterrows():
        if (value[1] == "Throughput full overlap"):
            throughput=value[2]
            #print("result:", value[2])

    new_dataframe={}
    new_dataframe["MP"]=mp
    new_dataframe["DP"]=dp
    new_dataframe["Stage"]=stages
    new_dataframe["Throughput"]=throughput
    #print(new_dataframe)
    return new_dataframe

def _parse_command_line_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--network_file', type=str)
    parser.add_argument('-c', '--configfile', type=str, help="base_param_config.yml")
    parser.add_argument('-o', '--outputfile', type=str, default="Report.csv")
    parser.add_argument('-cf', '--config_file', help='Specify the archbench configuration .yaml to use)')

    args = parser.parse_args(argv)
    return args

if __name__ == "__main__":

    # layerstat=archbench_run(sys.argv[1:])
    # print(layerstat)
    #archbench_run(sys.argv[1:])
    automated_graph_partitioning(sys.argv[1:])

#     planner_algorithm_obj=planner_algorithm()
#     planner_algorithm_obj.automated_graph_partitioning()