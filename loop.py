# python ./micro_service/dl-modelling.py summary -pc ./modelzoo/base_param_cfg.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12-SKUs-PVC.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-C0 --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 100 0


import os
import subprocess
import shutil
import pandas


freq_value = [1400,1600,500]
summary_dfs = []
workload  = ['SSD-ResNet34-300-BF16']# 'RESNET-50-MLPerf-BF16','BERT-LARGE-SEQ512-BF16','Mask-RCNN-1024-BF16' ,,'TransformerLanguageModel_1T']'TransformerLanguageModel_175B',
# workload  = ['RESNET-50-MLPerf-BF16']


# config_pair = [['PVC1T-512-C0-85-80','_PVCC_90Ser_1Card.yml']] # C step 1 card
# config_pair = [['PVC1T-512-C0-85-80','_PVCC_90Ser.yml']]  # C step 1 Node and 64 Node
# config_pair = [['PVC1T-512-B0-65','_PVCB_53Ser_1Card.yml']] #B step 1 card
# config_pair = [['PVC1T-512-B0-65','_PVCB_53Ser.yml']] # B step 1 Node and 64 Node
# config_pair = [['PVC1T-512-A0-HBM2p8','_PVCA_53Ser_1Card.yml']] # A step 1 card
# config_pair = [['PVC1T-512-A0-HBM2p8','_PVCA_53Ser.yml']] # A step 1 Node


# config_pair = [['PVC1T-512-B0-65','_PVCB_90Ser.yml']]
# config_pair = [['PVC1T-512-B0-65','_PVCB_53Ser_200Nic.yml']]
# config_pair = [['PVC1T-512-B0-65','_PVCB_90Ser_200Nic.yml']]
# config_pair = [['PVC1T-512-B0-65','_PVCB_90Ser.yml'],
#                ['PVC1T-512-B0-65','_PVCB_53Ser_200Nic.yml'],
#                ['PVC1T-512-B0-65','_PVCB_90Ser_200Nic.yml']]

# config_pair = [['PVC1T-512-B0-65','_PVCB_90Ser_glueless.yml']]
# config_pair = [['PVC1T-512-B0-65','_PVCB_53Ser_glueless.yml']]

config_pair = [['PVC1T-512-B0-65','_PVCB_53Ser_200Nic_8Nodes.yml']]


for wl in workload:
    for cf_p in config_pair:
        ab_filtersku = cf_p[0]
        param_config = './config_xt_xtplus/'+ str(wl) + '/' + str(wl) +str(cf_p[1])
        for freq in range(freq_value[0],freq_value[1],freq_value[2]):
            print("************************************************")
            print("Executing for freq (MHz):",freq)
            print("Executing for wl:", wl)
            print("Executing for SKU:", ab_filtersku)
            print("Executing for param_config:", param_config)
            print("************************************************")
            end = freq+99
            step =100
            output = "outdump_"+"{}".format(wl)+"_"+"{}".format(ab_filtersku)+"_freq_"+"{}".format(freq)+"_MHz"+str(cf_p[1][:-4])
            cmd = [
                        'python', './micro_service/dl-modelling.py', 'summary',
                        '-pc', "{}".format(param_config),
                        '-po', './modelzoo/Report.csv',
                        '-g', './ab-release-automation/ConfigSpecs/Gen12-SKUs-PVC.xlsx', #PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
                        '-w', './ab-release-automation/WorkloadSpecs/PVC-AtScale-Workloads.xlsx', #PVC-Workloads.xlsx
                        '-i', 'FALSE',
                        '-t', 'TRUE',
                        '--compderate', '0.95',
                        '--fusion', 'workload',
                        '--pipeline-backward-pass', 'TRUE',
                        '--flush-oversized-output-tensor', 'TRUE',
                        '--frequency', "{}".format(freq), "{}".format(end), "{}".format(step),
                        '-o', 'outdump',
                        '-s', 'AGGR',
                        '-a', 'run',
                        '--filtersku', "{}".format(ab_filtersku),
                        '--filter', "{}".format(wl),
                        '--dump_html',
                        '--upload'
                    ]

            subprocess.check_call(cmd)

            # summary_file = os.path.join("outdump", "AGGR", "AGGR-summary.csv")
            # summary_df = pandas.read_csv(summary_file)
            # summary_dfs.append(summary_df)
            if (os.path.exists(output)):
                if (os.path.exists(output+"_Bup")):
                    shutil.rmtree(output+"_Bup")
                os.rename(output,output+"_Bup")
            os.rename('outdump',output)
            subprocess.call(['cp','-r','modelzoo',output])
# aggr_df = pandas.concat(summary_dfs)
# aggr_df.to_csv("./modelzoo/loop-aggr-summary.csv", index=False)
