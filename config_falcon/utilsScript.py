import shutil
import os
from pvcSkuUpdate import pvcXtplusSku,rlt2tSku,adb2tSku,falcon1tSku,falcon2tSku
from ruamel import yaml

class createWorkloadFolder:
    def __init__(self,path):
        self.path = path

    def createFolder(self,pathToCreate):
        isExist = os.path.exists(pathToCreate)
        if isExist:
            print("-* Folder '{}' is already present, Creating fresh folder *-" .format(pathToCreate))
            shutil.rmtree(pathToCreate)
            os.mkdir(pathToCreate)
        else:
            print("-* Creating folder '{}'  *-".format(pathToCreate))
            os.mkdir(pathToCreate)

    def resnet50(self):
        folderName = 'RESNET-50-MLPerf-BF16'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def bertLarge(self):
        folderName = 'BERT-LARGE-SEQ512-BF16'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def ssdResnet(self):
        folderName = 'SSD-ResNet34-300-BF16'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def maskRCNN1024(self):
        folderName = 'Mask-RCNN-1024-BF16'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def transformer175b(self):
        folderName = 'TransformerLanguageModel_175B'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def transformer1t(self):
        folderName = 'TransformerLanguageModel_1T'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def transformer100t(self):
        folderName = 'TransformerLanguageModel_100T'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def graphSage(self):
        folderName = 'GraphSAGE'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def dlrmm4(self):
        folderName = 'DLRM_M4'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

    def dlrmmlperf(self):
        folderName = 'DLRM_MLperf'
        fullPath = self.path + folderName
        self.createFolder(fullPath)
        return

class dumpYaml:
    def __init__(self,config,workload,rootPath,sku):
        self.config = config
        self.workload = workload
        self.rootPath = rootPath
        self.sku = sku
        if self.sku == "pvcXtplus":
            self.pvcXtplusSkuDump()
        elif self.sku == "rlt2t":
            self.rlt2tSkuDump()
        elif self.sku == "adb2t":
            self.adb2tSkuDump()
        elif self.sku == "falcon1t":
            self.falcon1tSkuDump()
        elif self.sku == "falcon2t":
            self.falcon2tSkuDump()

    def pvcXtplusSkuDump(self):
        Config = pvcXtplusSku(self.config)
        pvcXtplusSkuNicBasedScaleoutConfig, \
        pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig, \
        pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig = Config.updatedConfig()
        tempList = [[pvcXtplusSkuNicBasedScaleoutConfig,"pvcXtplusSkuNicBasedScaleoutConfig"],
                    [pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig,"pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig"],
                    [pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig,"pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig"]]
        for fileName in tempList:
            fullPath = self.rootPath + self.workload + '/' + fileName[1] + '.yml'
            with open(fullPath, 'w') as dumpfile:
                yaml.dump(fileName[0], dumpfile, Dumper=yaml.RoundTripDumper)
        return

    def rlt2tSkuDump(self):
        Config = rlt2tSku(self.config)
        rlt2tSkuNicBasedScaleoutConfig, \
        rlt2tSkuPodBasedScaleoutCGRConfig, \
        rlt2tSkuNicBasedScaleoutRnrOpticsConfig, \
        rlt2tSkuPodBasedScaleoutRnrOpticsConfig = Config.updatedConfig()
        tempList = [[rlt2tSkuNicBasedScaleoutConfig,"rlt2tSkuNicBasedScaleoutConfig"],
                    [rlt2tSkuPodBasedScaleoutCGRConfig,"rlt2tSkuPodBasedScaleoutCGRConfig"],
                    [rlt2tSkuNicBasedScaleoutRnrOpticsConfig,"rlt2tSkuNicBasedScaleoutRnrOpticsConfig"],
                    [rlt2tSkuPodBasedScaleoutRnrOpticsConfig,"rlt2tSkuPodBasedScaleoutRnrOpticsConfig"]]
        for fileName in tempList:
            # print(fileName[1])
            fullPath = self.rootPath + self.workload + '/' + fileName[1] + '.yml'
            with open(fullPath, 'w') as dumpfile:
                yaml.dump(fileName[0], dumpfile, Dumper=yaml.RoundTripDumper)
        return

    def adb2tSkuDump(self):
        Config = adb2tSku(self.config)
        adb2tSkuNicBasedScaleoutConfig, \
        adb2tSkuPodBasedScaleoutRnrOptics7SoPortsConfig, \
        adb2tSkuPodBasedScaleoutRnrOptics5SoPortsConfig,\
        adb2tSkupodBasedScaleoutRnrOptics64Gbps7SoPortsConfig,\
        adb2tSkupodBasedScaleoutRnrOptics64Gbps14SoPortsConfig = Config.updatedConfig()
        #print(pvcXtplusSkuNicBasedScaleoutConfig)
        tempList = [[adb2tSkuNicBasedScaleoutConfig,"adb2tSkuNicBasedScaleoutConfig"],
                    [adb2tSkuPodBasedScaleoutRnrOptics7SoPortsConfig,"adb2tSkuPodBasedScaleoutRnrOptics7SoPortsConfig"],
                    [adb2tSkuPodBasedScaleoutRnrOptics5SoPortsConfig,"adb2tSkuPodBasedScaleoutRnrOptics5SoPortsConfig"],
                    [adb2tSkupodBasedScaleoutRnrOptics64Gbps7SoPortsConfig,"adb2tSkupodBasedScaleoutRnrOptics64Gbps7SoPortsConfig"],
                    [adb2tSkupodBasedScaleoutRnrOptics64Gbps14SoPortsConfig,"adb2tSkupodBasedScaleoutRnrOptics64Gbps14SoPortsConfig"]]
        for fileName in tempList:
            # print(fileName[1])
            fullPath = self.rootPath + self.workload + '/' + fileName[1] + '.yml'
            with open(fullPath, 'w') as dumpfile:
                yaml.dump(fileName[0], dumpfile, Dumper=yaml.RoundTripDumper)
        return

    def falcon1tSkuDump(self):
        Config = falcon1tSku(self.config)
        falcon1tSkuNicBasedScaleoutConfig, \
        falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig, \
        falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig = Config.updatedConfig()
        #print(pvcXtplusSkuNicBasedScaleoutConfig)
        tempList = [[falcon1tSkuNicBasedScaleoutConfig,"falcon1tSkuNicBasedScaleoutConfig"],
                    [falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig,"falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig"],
                    [falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig,"falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig"]]
        for fileName in tempList:
            # print(fileName[1])
            fullPath = self.rootPath + self.workload + '/' + fileName[1] + '.yml'
            with open(fullPath, 'w') as dumpfile:
                yaml.dump(fileName[0], dumpfile, Dumper=yaml.RoundTripDumper)
        return

    def falcon2tSkuDump(self):
        Config = falcon2tSku(self.config)
        falcon2tSkuNicBasedScaleoutWithT2TConfig, \
        falcon2tSkuNicBasedScaleoutWithOutT2TConfig, \
        falcon2tSkuPodBasedScaleoutRnrOpticsWithT2TConfig, \
        falcon2tSkuPodBasedScaleoutRnrOpticsWithOutT2TConfig = Config.updatedConfig()
        tempList = [[falcon2tSkuNicBasedScaleoutWithT2TConfig,"falcon2tSkuNicBasedScaleoutWithT2TConfig"],
                    [falcon2tSkuNicBasedScaleoutWithOutT2TConfig,"falcon2tSkuNicBasedScaleoutWithOutT2TConfig"],
                    [falcon2tSkuPodBasedScaleoutRnrOpticsWithT2TConfig,"falcon2tSkuPodBasedScaleoutRnrOpticsWithT2TConfig"],
                    [falcon2tSkuPodBasedScaleoutRnrOpticsWithOutT2TConfig,"falcon2tSkuPodBasedScaleoutRnrOpticsWithOutT2TConfig"]]
        for fileName in tempList:
            # print(fileName[1])
            fullPath = self.rootPath + self.workload + '/' + fileName[1] + '.yml'
            with open(fullPath, 'w') as dumpfile:
                yaml.dump(fileName[0], dumpfile, Dumper=yaml.RoundTripDumper)
        return