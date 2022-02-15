#!/bin/sh
#python ./micro_service/dl-modelling.py -f ./archbench/networks/BERT_enc_s512_lay24_c13_h16.py -cf ./archbench/configs/gen12-pvc.yaml -c ./modelzoo/config.csv -w ./modelzoo/comms.csv -wc ./modelzoo/compute.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv -wl ./modelzoo/BERT_enc_s512_lay24_c13_h16.py_graph_out.json
#for pvc in 16 32 64 128 256 512
#for nics in 2 #2 4
#do
jitter=0.3
pvc=16
nics=1
scaleout=1
path="$scaleout"_type #_"$pvc"PVC
cd "/home/sdg3/param/dl-modeling/param/src"
python change_config.py ../../modelzoo/base_config.csv --value sw_latency_in_us=7,use_pipeline=1,batch_size=16,serdes_rate_Gbps=112,include_jitter_to_scaleup=$jitter
python change_config_scaleout.py ../../modelzoo/base_config_scaleout.csv --value scaleout_type='flat',num_tiles_per_pvc=2,num_pvc=$pvc,num_PVC_per_host=8,BW_per_NIC_unidir_Gbps=400,num_NICs=$nics,include_jitter_to_scaleout=$jitter,scaleout_type_wrt_HW=$scaleout
cd -
mkdir $path
#python ./micro_service/dl-modelling.py summary -f ./archbench/networks/ResNet-50.prototxt -cf ./archbench/configs/gen12-pvc.yaml -c ./modelzoo/config.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv
#python ./micro_service/dl-modelling.py summary -f ./archbench/networks/BERT_enc_s512_lay24_c13_h16.py -cf ./archbench/configs/gen12-pvc.yaml -c ./modelzoo/config.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv
python ./micro_service/dl-modelling.py sweep -sp1 num_NICs -sr1 1,1,pow2 -f ./archbench/networks/BERT_enc_s200_lay12_c13_h12.py -cf ./archbench/configs/gen12-pvc.yaml -c ./modelzoo/config.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv
cp -r ./modelzoo/* $path
#python read_html.py $path/SpeedSimAnalysis.html
sleep 10
#done

#python ./micro_service/dl-modelling.py summary -f ./archbench/networks/BERT_enc_s200_lay12_c13_h12.py -cf ./archbench/configs/GEN_PVC1T.yaml --training --trg-greedy-flush True --trg-optimizer sgd --dump_html -c ./modelzoo/config.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv

python ./micro_service/dl-modelling.py summary -f ./archbench/networks/TransformerLanguageModel_17B.py -cf ./archbench/configs/GEN_PVC1T.yaml --training --trg-greedy-flush True --trg-optimizer sgd --dump_html -c ./modelzoo/config.csv -o ./modelzoo/Report.csv -so -so_config ./modelzoo/config_scaleout.csv



mv TransformerLanguageModel_175B_Kikker1.yml RESNET-50-MLPerf-BF16_Kikker1.yml
mv TransformerLanguageModel_175B_Kikker5.yml RESNET-50-MLPerf-BF16_Kikker5.yml
mv TransformerLanguageModel_175B_Kikker6.yml RESNET-50-MLPerf-BF16_Kikker6.yml
mv TransformerLanguageModel_175B_PVCB_53Ser.yml RESNET-50-MLPerf-BF16_PVCB_53Ser.yml
mv TransformerLanguageModel_175B_PVCB_90Ser.yml RESNET-50-MLPerf-BF16_PVCB_90Ser.yml
mv TransformerLanguageModel_175B_PVCC_90Ser.yml RESNET-50-MLPerf-BF16_PVCC_90Ser.yml

mv TransformerLanguageModel_175B_Kikker1.yml TransformerLanguageModel_1T_Kikker1.yml
mv TransformerLanguageModel_175B_Kikker5.yml TransformerLanguageModel_1T_Kikker5.yml
mv TransformerLanguageModel_175B_Kikker6.yml TransformerLanguageModel_1T_Kikker6.yml
mv TransformerLanguageModel_175B_PVCB_53Ser.yml TransformerLanguageModel_1T_PVCB_53Ser.yml
mv TransformerLanguageModel_175B_PVCB_90Ser.yml TransformerLanguageModel_1T_PVCB_90Ser.yml
mv TransformerLanguageModel_175B_PVCC_90Ser.yml TransformerLanguageModel_1T_PVCC_90Ser.yml

For Development and testing

python ./micro_service/dl-modelling.py summary -pc ./test/data/1T_transformer_zinf/TransformerLanguageModel_1T_PVCC_opt_glueless.yml -po ./modelzoo/Report.csv -g ./test/data/Gen12-SKUs-PVC.xlsx -w ./test/data/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE -o outdump -s AGGR -a run --filtersku PVC1T-512-C0-85-80 --filter TransformerLanguageModel_1T_meg --dump_html --frequency 1400 1500 100 
