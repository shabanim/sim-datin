# python ./micro_service/dl-modelling.py summary -pc ./modelzoo/base_param_cfg.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12-SKUs-PVC.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-C0 --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 100 0


import os
import subprocess
import shutil
import pandas


subprocess.check_call(['clear'])
freq_value = [1400,1500,100]
summary_dfs = []
workload  = ['RESNET-50-MLPerf-BF16','BERT-LARGE-SEQ512-BF16','TransformerLanguageModel_175B','TransformerLanguageModel_1T']#]
workload  = ['TransformerLanguageModel_175B']

# config_pair = [['PVC1T-512-C0-85-80','pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig.yml']]
# config_pair = [['PVC1T-512-C0-85-80','pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig.yml']]
# config_pair = [['PVC1T-512-C0-85-80','pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig.yml']]

# config_pair = [['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuNicBasedScaleoutConfig.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuNicBasedScaleoutRnrOpticsConfig.yml']]
# config_pair = [['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuPodBasedScaleoutRnrOpticsConfig.yml']]

# config_pair = [['ADB','adb2tSkuNicBasedScaleoutConfig.yml']]

# config_pair = [['ADB','falcon1tSkuNicBasedScaleoutConfig.yml']]

# config_pair = [['PVC1T-512-C0-85-80','pvcXtplusSkuNicBasedScaleoutConfig.yml'],
#                ['PVC1T-512-C0-85-80','pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig.yml'],
#                ['PVC1T-512-C0-85-80','pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig.yml'],
#                ['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuNicBasedScaleoutConfig.yml'],
#                ['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuNicBasedScaleoutRnrOpticsConfig.yml'],
#                ['RLT1T-1024-Plan-HBM23p6-NoADM-192L2','rlt2tSkuPodBasedScaleoutRnrOpticsConfig.yml'],
#                ['ADB','adb2tSkuNicBasedScaleoutConfig.yml'],
#                ['ADB','falcon1tSkuNicBasedScaleoutConfig.yml']]




for wl in workload:
    for cf_p in config_pair:
        ab_filtersku = cf_p[0]
        param_config = './config_falcon/'+ str(wl) + '/' + str(cf_p[1])
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
                        '-g', './ab-release-automation/ConfigSpecs/Falcon.xlsx', #PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
                        '-w', './ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx',
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
