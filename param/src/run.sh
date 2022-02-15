python3 change_config.py ../modelzoo/base_config.csv --value sw_latency_in_us=10,use_pipeline=1
python3 read_graph.py -c ../modelzoo/config.csv -g ../modelzoo/ResNet-50.prototxt_b32.nGraph.json
python3 comms_wrapper.py -c ../modelzoo/config.csv -w ../modelzoo/workload_resnet50.csv -wc ../modelzoo/compute_resnet50.csv