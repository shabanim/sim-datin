# python ./micro_service/dl-modelling.py summary -pc ./modelzoo/base_param_cfg.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12-SKUs-PVC.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-C0 --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 100 0


import os
import subprocess
import shutil
import pandas


subprocess.check_call(['clear'])
freq_value = [1668,1700,100]
summary_dfs = []
# workload  = ['RESNET-50-MLPerf-BF16','BERT-LARGE-SEQ512-BF16','TransformerLanguageModel_175B','TransformerLanguageModel_1T']#]
workload  = ['RESNET-50-MLPerf-BF16','BERT-LARGE-SEQ512-BF16']
# config_pair = [['RLT1T-1024-Plan-HBM3p2','_ANR_1.yml'],
#                ['RLT1T-1024-Plan-HBM3p6','_ANR_1.yml'],
#                ['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7.yml'],
#                ['RLT1T-1024-Plan-HBM3p6_ANR_1_7','_ANR_1_7.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM3p2','_ANR_1.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM3p6','_ANR_1.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM3p6_ANR_1_7','_ANR_1_7.yml']]

# config_pair = [['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7_1L_53Ser.yml'],
#                ['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7_1L_90Ser.yml'],
#                ['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7_2L_90Ser.yml'],
#                ['RLT1T-1024-Plan-HBM3p2_ANR_1_7','_ANR_1_7_5L_90Ser.yml']]

config_pair = [['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_Baseline.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config1.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config2.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config3.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config4.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config5.yml'],
               ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config6.yml']]

# config_pair = [['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_QR_RLT_576.yml'],
#                ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_QR_RLT_460.yml'],
#                ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_QR_RLT_288.yml'],
#                ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_QR_RLT_230.yml']]
#
# config_pair = [['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config4.yml'],
#                ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config5.yml'],
#                ['RLT1T-768-Plan-HBM3p2-ADM2.4-L3100','_ANR_light_config6.yml']]


for wl in workload:
    for cf_p in config_pair:
        ab_filtersku = cf_p[0]
        param_config = './config_RLT/'+ str(wl) + '/' + str(wl) +str(cf_p[1])
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
                        '-g', './ab-release-automation/ConfigSpecs/Gen12-SKUs-RLT-ADM.xlsx', #PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
                        '-w', './ab-release-automation/WorkloadSpecs/RLT-Workloads.xlsx',
                        '-i', 'FALSE',
                        '-t', 'TRUE',
                        '--compderate', '0.95',
                        '--fusion', 'workload',
                        '--pipeline-backward-pass', 'TRUE',
                        '--flush-oversized-output-tensor', 'TRUE',
                        '--frequency', "{}".format(freq), "{}".format(end), "{}".format(step),
                        '-o', 'outdump',
                        '-s', 'AGGR',
                        '-a', 'run_nb',
                        '--filtersku', "{}".format(ab_filtersku),
                        '--filter', "{}".format(wl),
                        '--dump_html'
                    ]

            subprocess.check_call(cmd)

            summary_file = os.path.join("outdump", "AGGR", "SUMMARY", "AGGR-summary.csv")
            summary_df = pandas.read_csv(summary_file)
            summary_dfs.append(summary_df)
            if (os.path.exists(output)):
                if (os.path.exists(output+"_Bup")):
                    shutil.rmtree(output+"_Bup")
                os.rename(output,output+"_Bup")
            os.rename('outdump',output)
            subprocess.call(['cp','-r','modelzoo',output])
aggr_df = pandas.concat(summary_dfs)
aggr_df.to_csv("./modelzoo/loop-aggr-summary.csv", index=False)
# subprocess.check_call(['rm', '-rf' , './modelzoo/rlt-training-overall.csv'])
# subprocess.check_call(['rm', '-rf' , './modelzoo/rlt-training-overall-ckp.csv'])
#
# subprocess.check_call(['python' ,
#                        'pack_results.py' ,
#                        '-i' , './modelzoo' ,
#                        '-o' , './modelzoo/rlt-training-overall.csv'
#                        ])
# subprocess.check_call(['pwd'])
# subprocess.check_call(['python' ,
#                        'add_checkpointing_perf.py' ,
#                        '-i' , './modelzoo/rlt-training-overall.csv' ,
#                        '-o' , './modelzoo/rlt-training-overall-ckp.csv',
#                        '-w', 'RESNET-50-MLPerf-FP32', 'RESNET-50-MLPerf-BF16', 'RESNET-50-MLPerf-TF32'
#                        ])
