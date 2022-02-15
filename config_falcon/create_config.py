from ruamel import yaml
from workloadUpdate import forWorkload
from utilsScript import createWorkloadFolder,dumpYaml
import os

intelGpuSku = ["pvcXtplus","rlt2t","adb2t" , "falcon1t" , "falcon2t"] # Can be "rlt2t" or "adb2t" or "falcon1t" or "falcon2t"
rootPath = "./1024tiles/"

#Load Base config file
with open('baseConfig.yml','r') as file:
    baseConfig = yaml.load(file,Loader=yaml.RoundTripLoader)


#Crete Updated copy for all Workload
workloads = forWorkload(baseConfig)
resnet50BaseConfig = workloads.resnet50()
bertLargeBaseConfig = workloads.bertLarge()
ssdResnetBaseConfig = workloads.ssdResnet()
maskRCNN1024BaseConfig = workloads.maskRCNN1024()
transformer175bBaseConfig = workloads.transformer175b()
transformer1tBaseConfig = workloads.transformer1t()
transformer100tBaseConfig = workloads.transformer100t()
graphSageBaseConfig = workloads.graphSage()
dlrmm4BaseConfig = workloads.dlrmm4()
dlrmmlperfBaseConfig = workloads.dlrmmlperf()
#Creat List  of  workload
workloadList = ["resnet50BaseConfig",
                "bertLargeBaseConfig",
                "ssdResnetBaseConfig",
                "maskRCNN1024BaseConfig",
                "transformer175bBaseConfig",
                "transformer1tBaseConfig",
                "transformer100tBaseConfig",
                "graphSageBaseConfig"]
# workloadList = ["resnet50BaseConfig",
#                 "bertLargeBaseConfig",
#                 "ssdResnetBaseConfig",
#                 "maskRCNN1024BaseConfig"]
# workloadList = ["dlrmm4BaseConfig"]
#workloadList = ["dlrmmlperfBaseConfig"]

#Create config folder for different workload
createFolder = createWorkloadFolder(rootPath)
createFolder.resnet50()
createFolder.bertLarge()
createFolder.ssdResnet()
createFolder.maskRCNN1024()
createFolder.transformer175b()
createFolder.transformer1t()
createFolder.transformer100t()
createFolder.graphSage()
createFolder.dlrmm4()
createFolder.dlrmmlperf()

#Create Configs for different workload with different intel GPU sku's
for sku in intelGpuSku:
    for workL in workloadList:
            if workL == "resnet50BaseConfig":
                dumpYaml(resnet50BaseConfig,'RESNET-50-MLPerf-BF16',rootPath,sku)
            elif workL == "bertLargeBaseConfig":
                dumpYaml(bertLargeBaseConfig, 'BERT-LARGE-SEQ512-BF16', rootPath,sku)
            elif workL == "ssdResnetBaseConfig":
                dumpYaml(ssdResnetBaseConfig, 'SSD-ResNet34-300-BF16', rootPath,sku)
            elif workL == "maskRCNN1024BaseConfig":
                dumpYaml(maskRCNN1024BaseConfig, 'Mask-RCNN-1024-BF16', rootPath,sku)
            elif workL == "transformer175bBaseConfig":
                dumpYaml(transformer175bBaseConfig, 'TransformerLanguageModel_175B', rootPath,sku)
            elif workL == "transformer1tBaseConfig":
                dumpYaml(transformer1tBaseConfig, 'TransformerLanguageModel_1T', rootPath,sku)
            elif workL == "transformer100tBaseConfig":
                dumpYaml(transformer100tBaseConfig, 'TransformerLanguageModel_100T', rootPath,sku)
            elif workL == "graphSageBaseConfig":
                dumpYaml(graphSageBaseConfig, 'GraphSAGE', rootPath,sku)
            elif workL == "dlrmm4BaseConfig":
                dumpYaml(dlrmm4BaseConfig, 'DLRM_M4', rootPath,sku)
            elif workL == "dlrmmlperfBaseConfig":
                dumpYaml(dlrmmlperfBaseConfig, 'DLRM_MLperf', rootPath,sku)

#print(baseConfig['Comms']['scaleup']['option'])
# print(yaml.dump(baseConfig, Dumper=yaml.RoundTripDumper), end='')

