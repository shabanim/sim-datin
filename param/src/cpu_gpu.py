import math
import json
import numpy as np
from .constants import Constants
from .zero import _get_optimizer_LayerID_for_zero

def zero_cpu_gpu_comms(knobs,netinfo):
    if knobs['ZeRO_type'] == 1 or knobs['ZeRO_type'] == 2:
        netinfo_out = netinfo

    elif knobs['ZeRO_type'] == 4:
        total_param = total_parameter(netinfo)
        # print("total_param:",total_param)
        wt_remote_storage_2_CPU_time_ms = 0
        for i in netinfo['nodes']:
            wt_grad_cpu_gpu_time_ms = 0
            wt_grad_nvme_cpu_time_ms = 0
            wt_cpu_gpu_time_ms = 0
            wt_nvme_cpu_time_ms = 0
            if (i['data']['Layer']['l_pass'])=='fwd' or (i['data']['Layer']['l_pass'])=='bwd-d':
                wt_cpu_gpu_time_ms = cpu_2_gpu(knobs,i['data']['Layer']['wt_grad_msg_size']) #P CPU-GPU
                wt_nvme_cpu_time_ms = cpu_2_nvme(knobs,i['data']['Layer']['wt_grad_msg_size']) #P NVME-CPU
            elif (i['data']['Layer']['l_pass'])=='bwd-w':
                wt_grad_cpu_gpu_time_ms = cpu_2_gpu(knobs,i['data']['Layer']['wt_grad_msg_size']) #W-G GPU-CPU
                wt_grad_nvme_cpu_time_ms = cpu_2_nvme(knobs, i['data']['Layer']['wt_grad_msg_size']) #W-G CPU-NVME
            elif (i['data']['Layer']['l_pass'])=='upd':
                if knobs['opt_name'] == 'adam':
                    k = 7
                    wt_nvme_cpu_time_ms = cpu_2_nvme(knobs,k*total_param,True)
                    wt_grad_nvme_cpu_time_ms = cpu_2_nvme(knobs, (k)*total_param,True)
                    numOfSockets = int(knobs['num_pvc']/knobs['num_PVC_per_host']*knobs['cpu_socket_per_node'])
                    i['data']['Layer']['fwd_pass_comp_cycles'] = i['data']['Layer']['fwd_pass_comp_cycles']*\
                                                                 knobs['ratioOfGpuRamBwtoCpuRamBw']/numOfSockets
                else:
                    exit("Error : Supports only adam opt")

            frequency_Ghz = float(knobs["frequency_in_Ghz"])
            i['data']['Layer']['wt_cpu_gpu_time_cycles'] = wt_cpu_gpu_time_ms*(1000000000*frequency_Ghz)/1000 #P CPU-GPU
            i['data']['Layer']['wt_nvme_cpu_time_cycles'] = wt_nvme_cpu_time_ms*(1000000000*frequency_Ghz)/1000 #P NVME-CPU
            i['data']['Layer']['wt_grad_cpu_gpu_time_cycles'] = wt_grad_cpu_gpu_time_ms*(1000000000*frequency_Ghz)/1000 #W-G GPU-CPU
            i['data']['Layer']['wt_grad_nvme_cpu_time_cycles'] = wt_grad_nvme_cpu_time_ms*(1000000000*frequency_Ghz)/1000 #W-G CPU-NVME
            i['data']['Layer']['comms_time_wt_cycles'] = i['data']['Layer']['comms_time_wtgrad_cycles']
            i['data']['Layer']['comms_scaleout_time_wt_cycles_nic'] = i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_nic']
            i['data']['Layer']['comms_scaleout_time_wt_cycles_pod'] = i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_pod']
            i['data']['Layer']['wt_collective_comms_type'] = i['data']['Layer']['wt_grad_collective_comms_type']

            if (i['data']['Layer']['l_pass']) == 'fwd' or (i['data']['Layer']['l_pass'])=='bwd-d':
                i['data']['Layer']['comms_time_wtgrad_cycles'] = 0
                i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_nic'] = 0
                i['data']['Layer']['comms_scaleout_time_wt_grad_cycles_pod'] = 0
                i['data']['Layer']['wt_grad_collective_comms_type'] = 0
            elif (i['data']['Layer']['l_pass']) == 'bwd-w':
                i['data']['Layer']['wt_grad_collective_comms_type'] = "reducescatter"
                i['data']['Layer']['comms_time_wt_cycles'] = 0
                i['data']['Layer']['comms_scaleout_time_wt_cycles_nic'] = 0
                i['data']['Layer']['comms_scaleout_time_wt_cycles_pod'] = 0
                i['data']['Layer']['wt_collective_comms_type'] = 0

            if (i['data']['Layer']['Layer Index']) == 0:
                if knobs['opt_name'] == 'adam':
                    k = 6
                else:
                    exit("Error : Supports only adam opt")
                i['data']['Layer']['wt_remote_storage_msg_size'] = total_param
                wt_remote_storage_2_CPU_time_ms = remote_2_cpu(knobs,k*float(i['data']['Layer']['wt_remote_storage_msg_size']))
                wt_remote_cpu_2_nvme_time_ms = cpu_2_nvme(knobs,k*float(i['data']['Layer']['wt_remote_storage_msg_size']))
                i['data']['Layer']['wt_remote_storage_2_CPU_cycles'] = wt_remote_storage_2_CPU_time_ms*(1000000000*frequency_Ghz)/1000
                i['data']['Layer']['wt_remote_cpu_2_nvme_cycles'] = wt_remote_cpu_2_nvme_time_ms * (
                            1000000000 * frequency_Ghz) / 1000
                data_remote_storage_2_CPU_time_ms = remote_2_cpu(knobs,(knobs['num_tiles_per_pvc']*knobs['num_pvc'])*
                                                                 float(i['data']['Layer']['data_remote_storage_msg_size']))
                data_remote_cpu_2_nvme_time_ms = cpu_2_nvme(knobs,(knobs['num_tiles_per_pvc']*knobs['num_pvc']) *
                                                            float(i['data']['Layer']['data_remote_storage_msg_size']))
                data_remote_cpu_2_gpu_time_ms = cpu_2_gpu(knobs,(knobs['num_tiles_per_pvc']*knobs['num_pvc']) *
                                                            float(i['data']['Layer']['data_remote_storage_msg_size']))
                i['data']['Layer']['data_remote_storage_2_CPU_cycles'] = data_remote_storage_2_CPU_time_ms * (
                            1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['data_remote_cpu_2_nvme_cycles'] = data_remote_cpu_2_nvme_time_ms * (
                        1000000000 * frequency_Ghz) / 1000
                i['data']['Layer']['data_remote_cpu_2_gpu_cycles'] = data_remote_cpu_2_gpu_time_ms * (
                        1000000000 * frequency_Ghz) / 1000
            elif (i['data']['Layer']['l_pass'])=='upd':
                i['data']['Layer']['wt_remote_storage_msg_size'] = total_param
                i['data']['Layer']['wt_remote_storage_2_CPU_cycles'] = wt_remote_storage_2_CPU_time_ms*(1000000000*frequency_Ghz)/1000
            else:
                i['data']['Layer']['wt_remote_storage_2_CPU_cycles'] = 0
                i['data']['Layer']['wt_remote_cpu_2_nvme_cycles'] = 0
                i['data']['Layer']['data_remote_storage_2_CPU_cycles'] = 0
                i['data']['Layer']['data_remote_cpu_2_nvme_cycles'] = 0
                i['data']['Layer']['data_remote_cpu_2_gpu_cycles'] = 0

        netinfo_out = netinfo

    return netinfo_out


def cpu_2_gpu(knobs,msg):
    if knobs['gpuDirectNVME']:
        cpu_2_gpu_time_ms = (((msg/Constants.GIGACONV)/(knobs['num_tiles_per_pvc']*knobs['num_pvc']))/knobs['gpuDirectNVMEbwGBpsPerTile'])*1000
    else:
        cpu_2_gpu_time_ms = (((msg/Constants.GIGACONV)/(knobs['num_tiles_per_pvc']*knobs['num_pvc']))/knobs['cpu_gpu_tile__pcie_BW_GBps'])*1000
    return cpu_2_gpu_time_ms

def cpu_2_nvme(knobs,msg,optimizer=False):
    Total_socket = (knobs['num_pvc']/knobs['num_PVC_per_host'])*knobs['cpu_socket_per_node']
    if knobs['disableNVME'] and knobs['gpuDirectNVME'] :
        exit("Error : Both disableNVME and gpuDirectNVME can not be True")
    else:
        if knobs['disableNVME']:
            cpu_2_nvme_time_ms = 0
        elif knobs['gpuDirectNVME']:
            if optimizer:
                cpu_2_nvme_time_ms = (((msg/Constants.GIGACONV)/Total_socket)/knobs['cpu_socket_NVME_pcie_BW_GBps'])*1000
            else:
                cpu_2_nvme_time_ms = 0
        else:
            cpu_2_nvme_time_ms = (((msg / Constants.GIGACONV) / Total_socket) / knobs[
                'cpu_socket_NVME_pcie_BW_GBps']) * 1000
    return cpu_2_nvme_time_ms

def total_parameter(netinfo):
    total_parameter = 0
    for i in netinfo['nodes']:
        if (i['data']['Layer']['l_pass']) == 'fwd':
            total_parameter = total_parameter + float(i['data']['Layer']['wt_grad_msg_size'])
    return total_parameter

def remote_2_cpu(knobs,msg):
    Total_nics = (knobs['num_pvc']/knobs['num_PVC_per_host'])*knobs['cpu_nics']
    Total_nic_BW_GBps = Total_nics * knobs['cpu_nic_bw_unidir_gbps'] * knobs['cpu_nic_eff'] / Constants.BYTE
    remote_2_cpu_time_ms = ((msg/Constants.GIGACONV)/Total_nic_BW_GBps)*1000
    return remote_2_cpu_time_ms