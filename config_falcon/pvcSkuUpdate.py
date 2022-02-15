import copy
class pvcXtplusSku:
    def __init__(self,baseConfig):
        self.baseConfig = baseConfig

    def nicBasedScaleout(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.85
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "flat"
        config['Comms']['scale_out']['hw_type'] = 1
        config['Device']['links'] = 7
        return config

    def nicBasedScaleoutRnrOptics(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 8
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        return config

    def podBasedScaleoutRnrOptics(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        return config

    def updatedConfig(self):
        pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig = self.nicBasedScaleoutRnrOptics()
        pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig = self.podBasedScaleoutRnrOptics()
        pvcXtplusSkuNicBasedScaleoutConfig = self.nicBasedScaleout()
        return pvcXtplusSkuNicBasedScaleoutConfig, \
               pvcXtplusSkuNicBasedScaleoutRnrOpticsConfig, \
               pvcXtplusSkuPodBasedScaleoutRnrOpticsConfig

class rlt2tSku:
    def __init__(self,baseConfig):
        self.baseConfig = baseConfig



    def nicBasedScaleout(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.85
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        config['Device']['links'] = 7
        return config

    def podBasedScaleoutCGR(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.85
        config['Device']['links'] = 7
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 32.85
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Collective']['scale_out_collectiveAlgo']['collective_method'] = "ring"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 4
        return config

    def nicBasedScaleoutRnrOptics(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        return config

    def podBasedScaleoutRnrOptics(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 32.5
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 450
        return config

    def updatedConfig(self):
        rlt2tSkuNicBasedScaleoutConfig = self.nicBasedScaleout()
        rlt2tSkuPodBasedScaleoutCGRConfig = self.podBasedScaleoutCGR()
        rlt2tSkuNicBasedScaleoutRnrOpticsConfig = self.nicBasedScaleoutRnrOptics()
        rlt2tSkuPodBasedScaleoutRnrOpticsConfig = self.podBasedScaleoutRnrOptics()
        return rlt2tSkuNicBasedScaleoutConfig, \
               rlt2tSkuPodBasedScaleoutCGRConfig, \
               rlt2tSkuNicBasedScaleoutRnrOpticsConfig, \
               rlt2tSkuPodBasedScaleoutRnrOpticsConfig

class adb2tSku:
    def __init__(self,baseConfig):
        self.baseConfig = baseConfig


    def nicBasedScaleout(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 540
        config['Device']['links'] = 12
        return config

    def podBasedScaleoutRnrOptics7SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 540
        config['Device']['links'] = 8
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        return config

    def podBasedScaleoutRnrOptics5SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 540
        config['Device']['links'] = 12
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 5
        return config

    def podBasedScaleoutRnrOptics64Gbps7SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 57.6
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 540
        config['Device']['links'] = 8
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 57.6
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        return config

    def podBasedScaleoutRnrOptics64Gbps14SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 800
        config['Device']['links'] = 16
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 14
        return config

    def updatedConfig(self):
        adb2tSkuNicBasedScaleoutConfig = self.nicBasedScaleout()
        adb2tSkuPodBasedScaleoutRnrOptics7SoPortsConfig = self.podBasedScaleoutRnrOptics7SoPorts()
        adb2tSkuPodBasedScaleoutRnrOptics5SoPortsConfig = self.podBasedScaleoutRnrOptics5SoPorts()
        adb2tSkupodBasedScaleoutRnrOptics64Gbps7SoPortsConfig = self.podBasedScaleoutRnrOptics64Gbps7SoPorts()
        adb2tSkupodBasedScaleoutRnrOptics64Gbps14SoPortsConfig = self.podBasedScaleoutRnrOptics64Gbps14SoPorts()
        return adb2tSkuNicBasedScaleoutConfig, \
               adb2tSkuPodBasedScaleoutRnrOptics7SoPortsConfig, \
               adb2tSkuPodBasedScaleoutRnrOptics5SoPortsConfig, \
               adb2tSkupodBasedScaleoutRnrOptics64Gbps7SoPortsConfig, \
               adb2tSkupodBasedScaleoutRnrOptics64Gbps14SoPortsConfig

class falcon1tSku:
    def __init__(self, baseConfig):
        self.baseConfig = baseConfig
        num_tiles_per_pvc = copy.deepcopy(baseConfig['Device']['num_tiles_per_pvc'])
        num_pvc = copy.deepcopy(baseConfig['Device']['num_pvc'])
        num_PVC_per_host = copy.deepcopy(baseConfig['Device']['num_PVC_per_host'])
        self.baseConfig['Device']['num_tiles_per_pvc'] = int(num_tiles_per_pvc/num_tiles_per_pvc)
        self.baseConfig['Device']['num_pvc'] = int(num_pvc * num_tiles_per_pvc)
        self.baseConfig['Device']['num_PVC_per_host'] = int(num_PVC_per_host * num_tiles_per_pvc)
        self.baseConfig['Comms']['cpu_socket_per_node']  = 16
        self.baseConfig['Comms']['cpu_gpu_tile__pcie_BW_GBps'] = 40
        self.falcon1tSkuNicBasedScaleoutConfig = self.nicBasedScaleout()
        self.falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig = self.podBasedScaleoutRnrOptics7SoPorts()
        self.falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig = self.podBasedScaleoutRnrOptics5SoPorts()

    def nicBasedScaleout(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 12
        return config

    def podBasedScaleoutRnrOptics7SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 8
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        config['Device']['pvc_inside_pod'] = 128
        return config

    def podBasedScaleoutRnrOptics5SoPorts(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 12
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 5
        config['Device']['pvc_inside_pod'] = 128
        return config

    def updatedConfig(self):
        falcon1tSkuNicBasedScaleoutConfig = self.nicBasedScaleout()
        falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig = self.podBasedScaleoutRnrOptics7SoPorts()
        falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig = self.podBasedScaleoutRnrOptics5SoPorts()
        return falcon1tSkuNicBasedScaleoutConfig, \
               falcon1tSkuPodBasedScaleoutRnrOptics7SoPortsConfig, \
               falcon1tSkuPodBasedScaleoutRnrOptics5SoPortsConfig

class falcon2tSku:
    def __init__(self, baseConfig):
        self.baseConfig = baseConfig


    def nicBasedScaleoutWithT2T(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 100
        config['Comms']['pipeline'] = False
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 12
        return config

    def nicBasedScaleoutWithOutT2T(self):
        config = copy.deepcopy(self.baseConfig)
        num_tiles_per_pvc = copy.deepcopy(self.baseConfig['Device']['num_tiles_per_pvc'])
        num_pvc = copy.deepcopy(self.baseConfig['Device']['num_pvc'])
        num_PVC_per_host = copy.deepcopy(self.baseConfig['Device']['num_PVC_per_host'])
        config['Device']['num_tiles_per_pvc'] = int(num_tiles_per_pvc / num_tiles_per_pvc)
        config['Device']['num_pvc'] = int(num_pvc * num_tiles_per_pvc)
        config['Device']['num_PVC_per_host'] = int(num_PVC_per_host * num_tiles_per_pvc)

        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 12
        return config

    def podBasedScaleoutRnrOpticsWithT2T(self):
        config = copy.deepcopy(self.baseConfig)
        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Device']['mdfi_BW_per_tile_ACHIEVABLE'] = 100
        config['Comms']['pipeline'] = False
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 8
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 7
        return config

    def podBasedScaleoutRnrOpticsWithOutT2T(self):
        config = copy.deepcopy(self.baseConfig)
        num_tiles_per_pvc = copy.deepcopy(self.baseConfig['Device']['num_tiles_per_pvc'])
        num_pvc = copy.deepcopy(self.baseConfig['Device']['num_pvc'])
        num_PVC_per_host = copy.deepcopy(self.baseConfig['Device']['num_PVC_per_host'])
        config['Device']['num_tiles_per_pvc'] = int(num_tiles_per_pvc / num_tiles_per_pvc)
        config['Device']['num_pvc'] = int(num_pvc * num_tiles_per_pvc)
        config['Device']['num_PVC_per_host'] = int(num_PVC_per_host * num_tiles_per_pvc)

        config['Comms']['su_BW_per_link_ACHIEVABLE_value'] = 45
        config['Comms']['scaleup']['option'] = "SWITCH"
        config['Device']['links'] = 8
        config['Comms']['so_BW_per_link_ACHIEVABLE_value'] = 45
        config['Collective']['scale_out_collectiveAlgo']['nw_topology'] = "pod"
        config['Comms']['scale_out']['hw_type'] = 7
        config['Device']['links_scaleout'] = 4
        return config

    def updatedConfig(self):
        falcon2tSkuNicBasedScaleoutWithT2TConfig = self.nicBasedScaleoutWithT2T()
        falcon2tSkuNicBasedScaleoutWithOutT2TConfig = self.nicBasedScaleoutWithOutT2T()
        falcon2tSkuPodBasedScaleoutRnrOpticsWithT2TConfig = self.podBasedScaleoutRnrOpticsWithT2T()
        falcon2tSkuPodBasedScaleoutRnrOpticsWithOutT2TConfig = self.podBasedScaleoutRnrOpticsWithOutT2T()
        return falcon2tSkuNicBasedScaleoutWithT2TConfig, \
               falcon2tSkuNicBasedScaleoutWithOutT2TConfig, \
               falcon2tSkuPodBasedScaleoutRnrOpticsWithT2TConfig, \
               falcon2tSkuPodBasedScaleoutRnrOpticsWithOutT2TConfig