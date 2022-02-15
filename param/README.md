# PARAM

Parameterized analytical model and trace generation tool

# Clone instruction
```
git clone https://gitlab.devtools.intel.com/ssridha2/param.git param
cd param
git fetch origin
git branch -a 
git checkout -b param_comms_integrated_1.2 remotes/origin/param_comms_integrated_1.2
```

#Graph Parser

To convert ResNet graph to param consumable format.
```
cd param/src
python3 read_graph.py -h
python3 read_graph.py -c ../modelzoo/config.csv -g ../modelzoo/ResNet-50.prototxt_b32.nGraph.json
```
#Execute PARAM

To execute param.
All the parameter in config files have to be configured based on requirement.
```
python3 comms_wrapper.py -h
python3 comms_wrapper.py -c ../modelzoo/config.csv -w ../modelzoo/workload_resnet50.csv -wc ../modelzoo/compute_resnet50.csv
```
To execute param-micro bench.
All the parameter in config files have to be configured based on requirement.
```
python3 comms_wrapper_ubench.py -h
python3 comms_wrapper_ubench.py -c ../modelzoo/config.csv -m 33280
```
To execute scaleout.
All the parameter in config files have to be configured based on requirement.
```
python3 scaleout_wrapper.py -c ../modelzoo/config_scaleout.csv
```
End to End run is provided in sample shell script "run.sh"
```
./run.sh
```