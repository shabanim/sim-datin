from graph_partitioning import MemoryFootprint
import os
from testcontext import PROJECT_DIR, EXPECTED_DIR, DATA_DIR, RESULTS_DIR

import subprocess
#class planner_algorithm:
def automated_graph_partitioning():
    mp=16
    print("mp")
    memory_dict={}
    while (mp<1024):
        dp=1024/mp
        #kernel=MemoryFootprint()
        memory_dict=MemoryFootprint.memory_footprint(r"C:\Users\aneriach\dl-modeling\results\results-GEN_PVC1T\TransformerLanguageModel_175B.py\TransformerLanguageModel_175B.py_layer_stat.csv",mp,dp)
        peak_memory= 64
        effective_memory=0.6*64
        for stages in memory_dict:
            if(memory_dict[stages]<effective_memory):
                print("MP={},DP={}".format(mp,dp))
                print("{}:{}".format(stages,memory_dict[stages]))
                #dl_modeling_flow()
        mp=mp*2


def dl_modeling_flow():
    cmd = [
        'python', './micro_service/dl-modelling.py', 'summary',
        '-f', "{}".format(os.path.join(DATA_DIR, '175B_transformer', 'TransformerLanguageModel_175B.py')),
        '-cf', "{}".format(os.path.join(DATA_DIR, '175B_transformer', 'GEN_PVC1T.yaml')),
        '-c', "{}".format(os.path.join(DATA_DIR, '175B_transformer', 'base_param_cfg.yml')),
        '-o', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
        '--training', '--trg-greedy-flush', 'True', '--trg-optimizer', 'adam', '--dump_html'
    ]
    subprocess.check_call(cmd)
    print("DONE")


if __name__ == "__main__":
    automated_graph_partitioning()
#     planner_algorithm_obj=planner_algorithm()
#     planner_algorithm_obj.automated_graph_partitioning()