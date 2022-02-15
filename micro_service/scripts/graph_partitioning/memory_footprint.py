#!/usr/bin/env python

import pandas as pd
class MemoryFootprint:
    def memory_footprint(csv_file,Nd,Nm,K=12):
        df =pd.read_csv(csv_file)
        #Nd=64
        #Nm=16
        B_2_GB = (1024*1024*1024)
        Dict1={}
        weight_sum=0
        for key,value in df.iterrows():
            if(value['Pass']=='fwd'):
                weight_sum+=value["Weight Size (Ki)"]
        #print("weight_sum",weight_sum)
        psi=(weight_sum*1024)/2
        #print("psi",psi)

        result_dict={}
        Baseline=((2+2+K)*psi)/Nm
        result_dict["Baseline_GB"]=Baseline/B_2_GB
        zero_stage_1=((2*psi)+(2*psi)+((K*psi)/Nd))/Nm
        result_dict["Zero_stage_1_GB"]=zero_stage_1/B_2_GB
        zero_stage_2=((2*psi)+(((2+K)*psi)/Nd))/Nm
        result_dict["Zero_stage_2_GB"]=zero_stage_2/B_2_GB
        zero_stage_3=(((2+2+K)*psi)/Nd)/Nm
        result_dict["Zero_stage_3_GB"]=zero_stage_3/B_2_GB
        return result_dict

if __name__ == "__main__":
    kernel=MemoryFootprint()
    Dict1=MemoryFootprint.memory_footprint(r"C:\Users\aneriach\dl-modeling\results\results-GEN_PVC1T\TransformerLanguageModel_175B.py\TransformerLanguageModel_175B.py_layer_stat.csv",16,64)

    print(Dict1)
#Dict1=memory_footprint(r"TransformerLT_Training.py_layer_stat.csv",64,16)

#Dict1=memory_footprint(r"C:\Users\aneriach\dl-modeling\results\results-GEN_PVC1T.bak\TransformerLanguageModel_17B.py\TransformerLanguageModel_17B.py_layer_stat.csv",16,64)
#print(Dict1)