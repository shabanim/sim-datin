# python ./micro_service/dl-modelling.py summary -pc ./config/RESNET-50-MLPerf-BF16/RESNET-50-MLPerf-BF16_PVCB_53Ser.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12_PVC-Kicker_Config_Compute_ANR_jason_r2.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-B0-53S --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 199 100

# python ./micro_service/dl-modelling.py summary -pc ./config/RESNET-50-MLPerf-BF16/RESNET-50-MLPerf-BF16_PVCB_53Ser.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12_PVC-Kicker_Config_Compute_ANR_jason_r2.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-B0-53S --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 199 100

import os
import subprocess
import shutil
import pandas


freq_value = [1400,1500,100]
summary_dfs = []
workload  = ['TransformerLanguageModel_1T']#['RESNET-50-MLPerf-BF16','BERT-LARGE-SEQ512-BF16']#,'DLRM_FB_SO','TransformerLanguageModel_175B','TransformerLanguageModel_1T']#[]#
# config_pair = [['PVC1T-512-B0-53S','_PVCB_53Ser.yml'],
#                ['PVC1T-512-B0-90S','_PVCB_90Ser.yml'],
#                ['PVC1T-512-C0-90S','_PVCC_90Ser.yml'],
#                ['PVCKicker1_Mem_1635_64GB','_Kikker1.yml'],
#                ['PVCKicker1_Mem_1635_64GB_ANR_1.7','_Kikker6.yml'],
#                ['PVCKicker2_Mem_3276_GB','_Kikker1.yml'],
#                ['PVCKicker2_Mem_3276_GB_ANR_1.7','_Kikker6.yml']]#,
               # ['PVCKicker3_32768_96GB', '_Kikker1b.yml'],
               # ['PVCKicker3_32768_96GB_1.7', '_Kikker6b.yml']]
#config_pair =[['PVC1T-512-B0-53S','_PVCB_53Ser.yml']]
config_pair =[['PVC1T-512-B0-90S','_PVCB_90Ser.yml']]
# config_pair =[['PVC1T-512-C0-90S','_PVCC_90Ser.yml']]
# config_pair =[['PVCKicker1_Mem_1635_64GB','_Kikker1.yml']]
# config_pair =[['PVCKicker1_Mem_1635_64GB_ANR_1.7','_Kikker6.yml']]
# config_pair =[['PVCKicker2_Mem_3276_GB','_Kikker1.yml']]
# config_pair =[['PVCKicker2_Mem_3276_GB_ANR_1.7','_Kikker6.yml']]
#config_pair =[['PVCKicker3_32768_96GB', '_Kikker1b.yml']]
#config_pair =[['PVCKicker3_32768_96GB_1.7', '_Kikker6b.yml']]

for wl in workload:
    for cf_p in config_pair:
        ab_filtersku = cf_p[0]
        param_config = './config_zinf/'+ str(wl) + '/' + str(wl) +str(cf_p[1])
        for freq in range(freq_value[0],freq_value[1],freq_value[2]):
            print("************************************************")
            print("Executing for freq (MHz):",freq)
            print("Executing for wl:", wl)
            print("Executing for SKU:", ab_filtersku)
            print("Executing for param_config:", param_config)
            print("************************************************")
            end = freq+99
            step =100
            output = "outdump_"+"{}".format(wl)+"_"+"{}".format(ab_filtersku)+"_freq_"+"{}".format(freq)+"_MHz"
            cmd = [
                        'python', './micro_service/dl-modelling.py', 'summary',
                        '-pc', "{}".format(param_config),
                        '-po', './modelzoo/Report.csv',
                        '-g', './ab-release-automation/ConfigSpecs/Gen12_PVC-Kicker_Config_Compute_ANR_jason_r2.xlsx', #PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx ,Gen12_PVC-Kicker_Config_Compute_ANR_jason_r2.xlsx'
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
                        '-a', 'run',
                        '--filtersku', "{}".format(ab_filtersku),
                        '--filter', "{}".format(wl),
                        '--dump_html'#,
                        #'--param-detailed-report'
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
