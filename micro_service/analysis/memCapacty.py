import csv
import ctypes

csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))


class memoryCapacy:
    def __init__(self,layerStat):
        self.layerStat = layerStat
        #self.knobs = knobs
        self.layerStatDict = self.openCsvfile()
        self.lengthOfDict = len(self.layerStatDict)
        self.getMemRequiredForDataParallelOrHybridParallel()
        self.getMemRequiredForZero2()
        self.getMemRequiredForZero2CpuOffload()
        self.getMemRequiredForZeroInfinity()


    def openCsvfile(self):
        with open(self.layerStat) as fin1:
            layerStatDict = [row for row in csv.DictReader(fin1)]
        return layerStatDict

    def getMemRequiredForDataParallelOrHybridParallel(self):
        activationSizeinKiBytes = 0
        inputGradSizeinKiBytes = 0
        weightSizeinKiBytes = 0
        weightGradSizeinKiBytes = 0
        #print(self.layerStatDict[0])
        for index in range(self.lengthOfDict):
            if self.layerStatDict[index]["Pass"] == "fwd" :
                activationSizeinKiBytes += float(self.layerStatDict[index]["Input Tensor Size (Ki)"])
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "oth":
                activationSizeinKiBytes += (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                            float(self.layerStatDict[index]["Output Tensor Size (Ki)"]))
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-d":
                inputGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-w":
                weightGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "upd":
                optimizerInputSizeinKiBytes = float(self.layerStatDict[index]["Input Tensor Size (Ki)"])
                optimizerOutputSizeinKiBytes = float(self.layerStatDict[index]["Output Tensor Size (Ki)"])

        # print("activationSizeinKiBytes:",activationSizeinKiBytes)
        # print("weightSizeinKiBytes:", weightSizeinKiBytes)
        # print("inputGradSizeinKiBytes:", inputGradSizeinKiBytes)
        # print("weightGradSizeinKiBytes:", weightGradSizeinKiBytes)
        # print("optimizerInputSizeinKiBytes:", optimizerInputSizeinKiBytes)
        # print("optimizerOutputSizeinKiBytes:", optimizerOutputSizeinKiBytes)

        memRequiredForWeightsinKiBytes = weightSizeinKiBytes
        memRequiredForWeightGradsinKiBytes = weightGradSizeinKiBytes
        memRequiredForActivationsinKiBytes = max(activationSizeinKiBytes,inputGradSizeinKiBytes)
        memRequiredForOptimizerinKiBytes = max(optimizerInputSizeinKiBytes,optimizerOutputSizeinKiBytes) - \
                                           max(weightSizeinKiBytes,weightGradSizeinKiBytes)
        
        totalMemRequiredinGiBytes = (memRequiredForWeightsinKiBytes + \
                                    memRequiredForWeightGradsinKiBytes + \
                                    memRequiredForActivationsinKiBytes + \
                                    memRequiredForOptimizerinKiBytes)/(1024*1024)

        print("totalMemRequiredinGiBytes for DP/HP:",totalMemRequiredinGiBytes)

    def getMemRequiredForZero2(self):
        activationSizeinKiBytes = 0
        inputGradSizeinKiBytes = 0
        weightSizeinKiBytes = 0
        weightGradSizeinKiBytes = 0
        numDataParallel = 8
        numOfStack = 96
        # print(self.layerStatDict[0])
        for index in range(self.lengthOfDict):
            if self.layerStatDict[index]["Pass"] == "fwd":
                activationSizeinKiBytes += float(self.layerStatDict[index]["Input Tensor Size (Ki)"])
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "oth":
                activationSizeinKiBytes += (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                            float(self.layerStatDict[index]["Output Tensor Size (Ki)"]))
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-d":
                inputGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-w":
                weightGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"]) / numDataParallel
            elif self.layerStatDict[index]["Pass"] == "upd":
                optimizerInputSizeinKiBytes = float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) / numDataParallel
                optimizerOutputSizeinKiBytes = float(self.layerStatDict[index]["Output Tensor Size (Ki)"]) / numDataParallel

        # print("activationSizeinKiBytes:",activationSizeinKiBytes)
        # print("weightSizeinKiBytes:", weightSizeinKiBytes)
        # print("inputGradSizeinKiBytes:", inputGradSizeinKiBytes)
        # print("weightGradSizeinKiBytes:", weightGradSizeinKiBytes)
        # print("optimizerInputSizeinKiBytes:", optimizerInputSizeinKiBytes)
        # print("optimizerOutputSizeinKiBytes:", optimizerOutputSizeinKiBytes)

        memRequiredForWeightsinKiBytes = weightSizeinKiBytes
        memRequiredForWeightGradsinKiBytes = weightGradSizeinKiBytes
        memRequiredForActivationsinKiBytes = max(activationSizeinKiBytes, inputGradSizeinKiBytes) / numOfStack
        memRequiredForOptimizerinKiBytes = max(optimizerInputSizeinKiBytes, optimizerOutputSizeinKiBytes) - \
                                           max(weightSizeinKiBytes / numDataParallel, weightGradSizeinKiBytes)

        totalMemRequiredinGiBytes = (memRequiredForWeightsinKiBytes + \
                                     memRequiredForWeightGradsinKiBytes + \
                                     memRequiredForActivationsinKiBytes + \
                                     memRequiredForOptimizerinKiBytes) / (1024 * 1024)

        print("totalMemRequiredinGiBytes for Zero2:", totalMemRequiredinGiBytes)

    def getMemRequiredForZero2CpuOffload(self):
        activationSizeinKiBytes = 0
        inputGradSizeinKiBytes = 0
        weightSizeinKiBytes = 0
        weightGradSizeinKiBytes = 0
        numDataParallel = 8
        numOfStack = 96
        # print(self.layerStatDict[0])
        for index in range(self.lengthOfDict):
            if self.layerStatDict[index]["Pass"] == "fwd":
                activationSizeinKiBytes += float(self.layerStatDict[index]["Input Tensor Size (Ki)"])
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "oth":
                activationSizeinKiBytes += (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                            float(self.layerStatDict[index]["Output Tensor Size (Ki)"]))
                weightSizeinKiBytes += float(self.layerStatDict[index]["Weight Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-d":
                inputGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"])
            elif self.layerStatDict[index]["Pass"] == "bwd-w":
                weightGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"]) / numDataParallel
            elif self.layerStatDict[index]["Pass"] == "upd":
                optimizerInputSizeinKiBytes = float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) / numDataParallel
                optimizerOutputSizeinKiBytes = float(self.layerStatDict[index]["Output Tensor Size (Ki)"]) / numDataParallel

        # print("activationSizeinKiBytes:",activationSizeinKiBytes)
        # print("weightSizeinKiBytes:", weightSizeinKiBytes)
        # print("inputGradSizeinKiBytes:", inputGradSizeinKiBytes)
        # print("weightGradSizeinKiBytes:", weightGradSizeinKiBytes)
        # print("optimizerInputSizeinKiBytes:", optimizerInputSizeinKiBytes)
        # print("optimizerOutputSizeinKiBytes:", optimizerOutputSizeinKiBytes)

        memRequiredForWeightsinKiBytes = weightSizeinKiBytes
        memRequiredForWeightGradsinKiBytes = 0 #weightGradSizeinKiBytes
        memRequiredForActivationsinKiBytes = max(activationSizeinKiBytes, inputGradSizeinKiBytes) / numOfStack
        memRequiredForOptimizerinKiBytes = 0 #max(optimizerInputSizeinKiBytes, optimizerOutputSizeinKiBytes) - max(weightSizeinKiBytes / numDataParallel, weightGradSizeinKiBytes)

        totalMemRequiredinGiBytes = (memRequiredForWeightsinKiBytes + \
                                     memRequiredForWeightGradsinKiBytes + \
                                     memRequiredForActivationsinKiBytes + \
                                     memRequiredForOptimizerinKiBytes) / (1024 * 1024)

        print("totalMemRequiredinGiBytes for Zero2 Offload:", totalMemRequiredinGiBytes)

    def getMemRequiredForZeroInfinity(self):
        activationSizeinKiBytes = 0
        instantActivationSizeinKiBytes = 0
        inputGradSizeinKiBytes = 0
        instantInputGradSizeinKiBytes = 0
        weightSizeinKiBytes = 0
        weightGradSizeinKiBytes = 0
        numOfStack = 96
        # print(self.layerStatDict[0])
        for index in range(self.lengthOfDict):
            if self.layerStatDict[index]["Pass"] == "fwd":
                activationSizeinKiBytes += float(self.layerStatDict[index]["Input Tensor Size (Ki)"])
                weightSizeinKiBytes = max(weightSizeinKiBytes,float(self.layerStatDict[index]["Weight Size (Ki)"]))
                instantActivationSizeinKiBytes = max(instantActivationSizeinKiBytes,
                                                     (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                                      float(self.layerStatDict[index]["Output Tensor Size (Ki)"])))
            elif self.layerStatDict[index]["Pass"] == "oth":
                activationSizeinKiBytes += (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                            float(self.layerStatDict[index]["Output Tensor Size (Ki)"]))
                weightSizeinKiBytes = max(weightSizeinKiBytes,float(self.layerStatDict[index]["Weight Size (Ki)"]))
                instantActivationSizeinKiBytes = max(instantActivationSizeinKiBytes,
                                                     (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                                      float(self.layerStatDict[index]["Output Tensor Size (Ki)"])))
            elif self.layerStatDict[index]["Pass"] == "bwd-d":
                inputGradSizeinKiBytes += float(self.layerStatDict[index]["Output Tensor Size (Ki)"])
                instantInputGradSizeinKiBytes = max(instantInputGradSizeinKiBytes,
                                                     (float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) +
                                                      float(self.layerStatDict[index]["Output Tensor Size (Ki)"])))
            elif self.layerStatDict[index]["Pass"] == "bwd-w":
                weightGradSizeinKiBytes = max(weightGradSizeinKiBytes,float(self.layerStatDict[index]["Output Tensor Size (Ki)"]))
            elif self.layerStatDict[index]["Pass"] == "upd":
                optimizerInputSizeinKiBytes = 0 #float(self.layerStatDict[index]["Input Tensor Size (Ki)"]) / numDataParallel
                optimizerOutputSizeinKiBytes = 0 #float(self.layerStatDict[index]["Output Tensor Size (Ki)"]) / numDataParallel

        # print("activationSizeinKiBytes:",activationSizeinKiBytes)
        # print("weightSizeinKiBytes:", weightSizeinKiBytes)
        # print("inputGradSizeinKiBytes:", inputGradSizeinKiBytes)
        # print("weightGradSizeinKiBytes:", weightGradSizeinKiBytes)
        # print("optimizerInputSizeinKiBytes:", optimizerInputSizeinKiBytes)
        # print("optimizerOutputSizeinKiBytes:", optimizerOutputSizeinKiBytes)
        # print("instantActivationSizeinKiBytes:", instantActivationSizeinKiBytes)
        # print("instantInputGradSizeinKiBytes:", instantInputGradSizeinKiBytes)

        memRequiredForWeightsinKiBytes = weightSizeinKiBytes
        memRequiredForWeightGradsinKiBytes = weightGradSizeinKiBytes
        memRequiredForActivationsinKiBytes = activationSizeinKiBytes / numOfStack
        memRequiredForInstantActivationsinKiBytes = max(instantActivationSizeinKiBytes, instantInputGradSizeinKiBytes)
        memRequiredForOptimizerinKiBytes = 0 #max(optimizerInputSizeinKiBytes, optimizerOutputSizeinKiBytes) - max(weightSizeinKiBytes / numDataParallel, weightGradSizeinKiBytes)

        totalMemRequiredinGiBytes = (memRequiredForWeightsinKiBytes + \
                                     memRequiredForWeightGradsinKiBytes + \
                                     memRequiredForActivationsinKiBytes + \
                                     memRequiredForOptimizerinKiBytes +
                                     memRequiredForInstantActivationsinKiBytes) / (1024 * 1024)

        print("totalMemRequiredinGiBytes for Zero infinity:", totalMemRequiredinGiBytes)


memoryCapacy("./BERT_Large_Pretraining.py_layer_stat.csv")
    