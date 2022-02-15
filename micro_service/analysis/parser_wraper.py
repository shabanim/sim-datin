import parser_train
from utils import *

string1="encoder_ffn2_1"
# print(string1)
#
#
a,b = model_split_file_read("/home/sdg3/param/dl-modeling/micro_service/analysis/transformer_split.csv")
# print(a)
# print(b)
for item in a:

    if (item["Name"] in string1 ):
        print(item)

a=read_config("/home/sdg3/param/dl-modeling/modelzoo/config.csv")
a['outFilePath']='./'
a['frequency_in_Ghz'] = 1.7
# parser_train.parse_graph(a, "/home/sdg3/arch_bench/archbench/results/PVC1T/BERT_enc_s200_lay12_c13_h12.py/BERT_enc_s200_lay12_c13_h12.py_graph.json",
#                          "/home/sdg3/arch_bench/archbench/results/PVC1T/BERT_enc_s200_lay12_c13_h12.py/BERT_enc_s200_lay12_c13_h12.py_stats_200.0MB_CMX_FSPS.csv",
#                          "/home/sdg3/arch_bench/archbench/results/PVC1T/BERT_enc_s200_lay12_c13_h12.py/BERT_enc_s200_lay12_c13_h12.py_layer_stat.csv")
parser_train.parse_graph(a, "/home/sdg3/arch_bench/archbench/results/PVC1T/TransformerLanguageModel_17B.py/TransformerLanguageModel_17B.py_graph.json",
                         "/home/sdg3/arch_bench/archbench/results/PVC1T/TransformerLanguageModel_17B.py/TransformerLanguageModel_17B.py_stats_200.0MB_CMX_FSPS.csv",
                         "/home/sdg3/arch_bench/archbench/results/PVC1T/TransformerLanguageModel_17B.py/TransformerLanguageModel_17B.py_layer_stat.csv")