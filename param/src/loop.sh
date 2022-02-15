for i in 0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 1.5 1.6 1.7 1.8 1.9 2.0 2.1
do
#i=1.5
clear
cd ../modelzoo/
echo "frequency_in_Ghz,$i" >> config.csv
echo "frequency_in_Ghz,$i" >> /home/sdg3/param/param/src/report_50mb_fusion.csv
cat config.csv
sleep 2
cd -
python3 read_graph.py -c ../modelzoo/config.csv -g ../modelzoo/ResNet-50.prototxt_b32.nGraph.json
sleep 2
python3 comms_wrapper.py -c ../modelzoo/config.csv -w ../modelzoo/workload_resnet50.csv -wc ../modelzoo/compute_resnet50.csv
sleep 2
mv Report.csv Report_1C_"$i"freq.csv

#python3 comms_wrapper_ubench.py -c ../modelzoo/config.csv -m 52428800 >> /home/sdg3/param/param/src/report_50mb_fusion.csv
cd ../modelzoo/
sed -i '$d' config.csv
cat config.csv
sleep 2
cd -
done



