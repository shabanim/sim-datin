# python ./micro_service/dl-modelling.py summary -pc ./modelzoo/base_param_cfg.yml -po ./modelzoo/Report.csv -g ./ab-release-automation/ConfigSpecs/Gen12-SKUs-PVC.xlsx -w ./ab-release-automation/WorkloadSpecs/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-C0 --filter RESNET-50-MLPerf-BF16 --dump_html --frequency 100 100 0


import os
import subprocess
import shutil
import pandas


subprocess.check_call(['clear'])
freq_value = [1400,1500,100]
summary_dfs = []
workload  = ['RESNET-50-MLPerf-BF16']#,'BERT-LARGE-SEQ512-BF16','TransformerLanguageModel_175B','TransformerLanguageModel_1T']
# config_pair = [['PVC1T-512-C0-90S','AI_53se.yml'],
#                ['PVC1T-512-C0-90S','AI_90se.yml']]
# config_pair = [['PVC1T-512-B0-65','AI_53se.yml']]
config_pair = [ ['PVC1T-448-B0-65','Aurora_53se.yml']]

# config_pair = [ ['PVC1T-512-C0-90S','Aurora_53se.yml'],
#                ['PVC1T-512-C0-90S','Aurora_90se.yml']]


for wl in workload:
    for cf_p in config_pair:
        ab_filtersku = cf_p[0]
        param_config = './config_cluster/'+ str(wl) + '/' + str(cf_p[1])
        for freq in range(freq_value[0],freq_value[1],freq_value[2]):
            print("************************************************")
            print("Executing for freq (MHz):",freq)
            print("Executing for wl:", wl)
            print("Executing for SKU:", ab_filtersku)
            print("Executing for param_config:", param_config)
            print("************************************************")
            end = freq+99
            step =100
            output = "outdump_"+"{}".format(wl)+"_"+str(cf_p[1])[:-4]+"{}".format(freq)
            cmd = [
                        'python', './micro_service/dl-modelling.py', 'summary',
                        '-pc', "{}".format(param_config),
                        '-po', './modelzoo/Report.csv',
                        '-g', './ab-release-automation/ConfigSpecs/A21-PVC-SKUs.xlsx', #PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx A21-PVC-SKUs.xlsx
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


            if (os.path.exists(output)):
                if (os.path.exists(output+"_Bup")):
                    shutil.rmtree(output+"_Bup")
                os.rename(output,output+"_Bup")
            os.rename('outdump',output)
            subprocess.call(['cp','-r','modelzoo',output])
