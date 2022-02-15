import copy

class forWorkload:
    def __init__(self,baseConfig):
        self.baseConfig = baseConfig

    def resnet50(self):
        self.resnet50BaseConfig = copy.deepcopy(self.baseConfig)
        self.resnet50BaseConfig['Comms']['use_buffer'] = True
        self.resnet50BaseConfig['Comms']['ZeRO_type'] = 2
        if self.resnet50BaseConfig['Device']['num_pvc'] == 1:
            self.resnet50BaseConfig['Comms']['pipeline'] = False
        return self.resnet50BaseConfig

    def bertLarge(self):
        self.bertLargeBaseConfig = copy.deepcopy(self.baseConfig)
        self.bertLargeBaseConfig['Comms']['use_buffer'] = True
        self.bertLargeBaseConfig['Comms']['ZeRO_type'] = 2
        if self.bertLargeBaseConfig['Device']['num_pvc'] == 1:
            self.bertLargeBaseConfig['Comms']['pipeline'] = False
        return self.bertLargeBaseConfig

    def ssdResnet(self):
        self.ssdResnetBaseConfig = copy.deepcopy(self.baseConfig)
        self.ssdResnetBaseConfig['Comms']['use_buffer'] = True
        self.ssdResnetBaseConfig['Comms']['ZeRO_type'] = 2
        if self.ssdResnetBaseConfig['Device']['num_pvc'] == 1:
            self.ssdResnetBaseConfig['Comms']['pipeline'] = False
        return self.ssdResnetBaseConfig

    def maskRCNN1024(self):
        self.maskRCNN1024BaseConfig = copy.deepcopy(self.baseConfig)
        self.maskRCNN1024BaseConfig['Comms']['use_buffer'] = True
        self.maskRCNN1024BaseConfig['Comms']['ZeRO_type'] = 2
        if self.maskRCNN1024BaseConfig['Device']['num_pvc'] == 1:
            self.maskRCNN1024BaseConfig['Comms']['pipeline'] = False
        return self.maskRCNN1024BaseConfig

    def transformer175b(self):
        self.transformer175bBaseConfig = copy.deepcopy(self.baseConfig)
        self.transformer175bBaseConfig['Comms']['data_parallel'] = False
        self.transformer175bBaseConfig['Comms']['Enable_ZeRO'] = True
        self.transformer175bBaseConfig['Comms']['Zero-inf'] = True
        self.transformer175bBaseConfig['Comms']['fwd_2x'] = True
        self.transformer175bBaseConfig['Comms']['ZeRO_type'] = 4
        return self.transformer175bBaseConfig

    def transformer1t(self):
        self.transformer1tBaseConfig = copy.deepcopy(self.baseConfig)
        self.transformer1tBaseConfig['Comms']['data_parallel'] = False
        self.transformer1tBaseConfig['Comms']['Enable_ZeRO'] = True
        self.transformer1tBaseConfig['Comms']['Zero-inf'] = True
        self.transformer1tBaseConfig['Comms']['fwd_2x'] = True
        self.transformer1tBaseConfig['Comms']['ZeRO_type'] = 4
        return self.transformer1tBaseConfig

    def transformer1tZero2(self):
        self.transformer1tBaseConfig = copy.deepcopy(self.baseConfig)
        self.transformer1tBaseConfig['Comms']['data_parallel'] = False
        self.transformer1tBaseConfig['Comms']['Enable_ZeRO'] = True
        self.transformer1tBaseConfig['Comms']['Zero-inf'] = False
        self.transformer1tBaseConfig['Comms']['fwd_2x'] = True
        self.transformer1tBaseConfig['Comms']['ZeRO_type'] = 2
        self.transformer1tBaseConfig['Comms']['model_split'] = 128
        self.transformer1tBaseConfig['Comms']['enable_2x'] = True
        return self.transformer1tBaseConfig

    def transformer100t(self):
        self.transformer100tBaseConfig = copy.deepcopy(self.baseConfig)
        self.transformer100tBaseConfig['Comms']['data_parallel'] = False
        self.transformer100tBaseConfig['Comms']['Enable_ZeRO'] = True
        self.transformer100tBaseConfig['Comms']['Zero-inf'] = True
        self.transformer100tBaseConfig['Comms']['fwd_2x'] = True
        self.transformer100tBaseConfig['Comms']['ZeRO_type'] = 4
        return self.transformer100tBaseConfig

    def graphSage(self):
        self.graphSageBaseConfig = copy.deepcopy(self.baseConfig)
        self.graphSageBaseConfig['Comms']['use_buffer'] = True
        self.graphSageBaseConfig['Comms']['data_parallel'] = False
        self.graphSageBaseConfig['Comms']['hybrid_model'] = True
        self.graphSageBaseConfig['Comms']['model_split'] = int(self.graphSageBaseConfig['Device']['num_tiles_per_pvc'] *
                                                               self.graphSageBaseConfig['Device']['num_pvc'])
        self.graphSageBaseConfig['Comms']['ZeRO_type'] = 2
        self.graphSageBaseConfig['Comms']['DLRM'] = False
        self.graphSageBaseConfig['Comms']['Zero-inf'] = False
        self.graphSageBaseConfig['Comms']['graph_split_csv'] = "./modelzoo/graph_split/GNN_split.csv"

        return self.graphSageBaseConfig

    def dlrmm4(self):
        self.dlrmm4BaseConfig = copy.deepcopy(self.baseConfig)
        self.dlrmm4BaseConfig['Comms']['data_parallel'] = False
        self.dlrmm4BaseConfig['Comms']['hybrid_model'] = True
        self.dlrmm4BaseConfig['Comms']['Enable_ZeRO'] = False
        self.dlrmm4BaseConfig['Comms']['Zero-inf'] = False
        self.dlrmm4BaseConfig['Comms']['DLRM'] = True
        self.dlrmm4BaseConfig['Comms']['GPU_direct'] = False
        self.dlrmm4BaseConfig['Comms']['PMEM'] = False
        self.dlrmm4BaseConfig['Comms']['fwd_2x'] = False
        self.dlrmm4BaseConfig['Comms']['ZeRO_type'] = 2
        self.dlrmm4BaseConfig['Device']['num_pvc'] = 64
        self.dlrmm4BaseConfig['Comms']['model_split'] = 128
        self.dlrmm4BaseConfig['Comms']['graph_split_csv'] = "./modelzoo/graph_split/DLRM_split_m4_table.csv"
        self.dlrmm4BaseConfig['Comms']['use_buffer'] = True
        self.dlrmm4BaseConfig['Comms']['buffer_size'] = 1048576000
        return self.dlrmm4BaseConfig

    def dlrmmlperf(self):
        self.dlrmm4BaseConfig = copy.deepcopy(self.baseConfig)
        self.dlrmm4BaseConfig['Comms']['data_parallel'] = False
        self.dlrmm4BaseConfig['Comms']['hybrid_model'] = True
        self.dlrmm4BaseConfig['Comms']['Enable_ZeRO'] = False
        self.dlrmm4BaseConfig['Comms']['Zero-inf'] = False
        self.dlrmm4BaseConfig['Comms']['DLRM'] = False
        self.dlrmm4BaseConfig['Comms']['fwd_2x'] = False
        self.dlrmm4BaseConfig['Comms']['ZeRO_type'] = 2
        self.dlrmm4BaseConfig['Device']['num_pvc'] = 8
        self.dlrmm4BaseConfig['Comms']['model_split'] = 16
        self.dlrmm4BaseConfig['Comms']['graph_split_csv'] = "./modelzoo/graph_split/DLRM_split.csv"
        self.dlrmm4BaseConfig['Comms']['use_buffer'] = True
        self.dlrmm4BaseConfig['Comms']['buffer_size'] = 1048576000
        return self.dlrmm4BaseConfig