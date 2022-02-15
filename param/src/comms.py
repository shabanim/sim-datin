import numpy as np
import math



def combine_compute_comms(final_time,compute_time):
    if len(final_time) == len(compute_time):
        compute_comms_time = [[]] * len(compute_time)
        total_comms_time_with_overlap_wtgrad = [[]] * len(final_time)
        for i in reversed(range(len(final_time))):
            if final_time[i][0] == compute_time[i][0]:
                if final_time[i][0] == int(max(np.asarray(compute_time)[:,0])): #len(final_time):
                    total_comms_time_with_overlap_wtgrad[i] = (final_time[i][3] - compute_time[i - 1][2]) \
                        if final_time[i][3] > compute_time[i - 1][2] else 0
                elif final_time[i][0] == int(min(np.asarray(compute_time)[:,0])): #1:
                    total_comms_time_with_overlap_wtgrad[i] = final_time[i][3] + total_comms_time_with_overlap_wtgrad[
                        i + 1]
                else:
                    total_comms_time_with_overlap_wtgrad[i] = ((final_time[i][3] - compute_time[i - 1][2])
                                                               if final_time[i][3] > compute_time[i - 1][2]
                                                               else 0) + total_comms_time_with_overlap_wtgrad[i + 1]
        # print(total_comms_time_with_overlap_wtgrad)

        for i in range(len(final_time)):
            if final_time[i][0] == compute_time[i][0]:
                if final_time[i][0] == int(min(np.asarray(compute_time)[:,0])):
                    total_comms_time_without_overlap = final_time[i][1] + final_time[i][3]
                    total_comms_time_with_overlap = 0

                else:
                    total_comms_time_without_overlap = final_time[i][1] + final_time[i][2] + final_time[i][3]
                    total_comms_time_with_overlap = (final_time[i][2] - compute_time[i][3]) \
                        if final_time[i][2] > compute_time[i][3] else 0
                total_compute_time_without_comms = compute_time[i][1] + compute_time[i][2] + compute_time[i][3]
                compute_comms_time[i] = [compute_time[i][0], compute_time[i][1], compute_time[i][2], compute_time[i][3],
                                         final_time[i][1], final_time[i][2], final_time[i][3],
                                         total_comms_time_without_overlap,
                                         total_comms_time_with_overlap_wtgrad[i], total_comms_time_with_overlap,
                                         total_compute_time_without_comms,final_time[i][4]]
                # print(compute_comms_time[i])
            else:
                print("layer id mismatch")
    else:
        print("# of layers mismatch")
    return compute_comms_time

def combine_compute_comms_no_overlap(final_time,compute_time):
    if len(final_time) == len(compute_time):
        compute_comms_time = [[]] * len(compute_time)
        for i in range(len(final_time)):
            if final_time[i][0] == compute_time[i][0]:
                compute_comms_time[i] = [compute_time[i][0], compute_time[i][1], compute_time[i][2], compute_time[i][3],
                                         final_time[i][1], final_time[i][2], final_time[i][3]]
                # print(compute_comms_time[i])
            else:
                print("layer id mismatch")
    else:
        print("# of layers mismatch")
    return compute_comms_time

def calc_time_and_effic(compute_comms_time,total_comute_time_no_IP_wt_GRAD):

    compute_comms_time=np.asarray(compute_comms_time)

    Comms_time = np.sum(compute_comms_time[0:(len(compute_comms_time)),4]) + \
                 np.sum(compute_comms_time[0:(len(compute_comms_time)),9]) + \
                 compute_comms_time[0,8]
    total_compute_time_with_comms_full_overlap=np.sum(compute_comms_time[0:(len(compute_comms_time)),10]) + Comms_time +total_comute_time_no_IP_wt_GRAD
    total_compute_time_without_comms =np.sum(compute_comms_time[0:(len(compute_comms_time)),10]) + total_comute_time_no_IP_wt_GRAD
    Scaling_Efficiency_full_overlap = total_compute_time_without_comms/total_compute_time_with_comms_full_overlap
    total_compute_plus_comms_without_overlap =np.sum(compute_comms_time[0:(len(compute_comms_time)),4:7])+ \
                                              np.sum(compute_comms_time[0:(len(compute_comms_time)),10])+\
                                              total_comute_time_no_IP_wt_GRAD
    scaling_efficiency=total_compute_time_without_comms/total_compute_plus_comms_without_overlap
    total_comms_with_relastic_overlap_only_w_grad =np.sum(compute_comms_time[0:(len(compute_comms_time)),4:6])+ \
                                              np.sum(compute_comms_time[0:(len(compute_comms_time)),10])+\
                                                   compute_comms_time[0,8]+total_comute_time_no_IP_wt_GRAD
    Scaling_efficiency_with_relastic_overlap_only_w_grad =total_compute_time_without_comms/\
                                                          total_comms_with_relastic_overlap_only_w_grad
    return [Comms_time,total_compute_time_with_comms_full_overlap,total_compute_time_without_comms,Scaling_Efficiency_full_overlap,
           total_compute_plus_comms_without_overlap,scaling_efficiency,total_comms_with_relastic_overlap_only_w_grad,
           Scaling_efficiency_with_relastic_overlap_only_w_grad]

class Comms():
    def __init__(self,coms_arg,config):#, scale_opt, args, nnodes, rand_seed, tiles_per_card):
        #print('in comms')
        self.add_noise = 0 #args.add_noise
        self.tiles_per_card = int((coms_arg["tile_per_socket"])) #tiles_per_card
        self.sw_latency_in_us =int(config["sw_latency_in_us"])
        self.L3_read_cache_miss_for_data_from_remote_write =int(config["L3_read_cache_miss_for_data_from_remote_write"]) #cycles
        self.L3_read_cache_miss_on_sync_flag =int(config["L3_read_cache_miss_on_sync_flag"]) #cycles
        self.thread_dispatch =int(config["thread_dispatch"])
        self.L3_write_cache_hit_on_data =int(config["L3_write_cache_hit_on_data"])
        self.L3_write_cache_hit_on_sync_flag =int(config["L3_write_cache_hit_on_sync_flag"])
        self.L1_hit_per_cache_line =int(config["L1_hit_per_cache_line"])
        self.frequency_in_Ghz =float(config["frequency_in_Ghz"])
        self.mdfi_link_latency =int(config["mdfi_link_latency"])
        self.scale_up_option = config["scale_up_option"] #'GLUELESS' #'SWITCH'#
        self.no_of_dss_or_sms =int(config["no_of_dss_or_sms"])
        self.read_memBW_per_dss =int(config["global_memory_reads"]) * self.frequency_in_Ghz
        self.write_memBW_per_dss = int(config["global_memory_writes"]) * self.frequency_in_Ghz
        self.max_achievable_read_memBW_no_congession =int(config["peak_read_memBW"]) *  float(config["read_memory_efficiency"])
        self.max_achievable_write_memBW_no_congession = int(config["peak_write_memBW"]) *  float(config["write_memory_efficiency"])
        self.message_size =int(float(coms_arg["msg_size"]))
        self.gigaconv = 1024 * 1024 * 1024
        self.nsockets =int(coms_arg["no_socket"])
        #print(self.nsockets)
        self.no_of_concurrent_messages_over_scale_up =int(config["no_of_concurrent_messages_over_scale_up"])
        self.no_of_concurrent_messages_over_mdfi = 0 if (self.tiles_per_card/2)<1 else (self.tiles_per_card/2)
        self.local_write_scale_up =int(config["local_write_scale_up"])


        self.mdfi_BW_per_tile_ACHIEVABLE =int(config["mdfi_BW_per_tile_ACHIEVABLE"])
        self.no_of_links =int(config["no_of_links"])
        self.scale_up_link_efficiency = float(config["scale_up_link_efficiency"])
        self.fabric_efficiency = self.scale_up_link_efficiency * float(config["scale_up_packet_size"]) / (
                    float(config["scale_up_packet_size"]) + float(config["scale_up_Message header"]) + float(
                config["scale_up_packet_response"]))
        self.serdes_lane = 4
        self.byte = 8
        if config['scale_out_flag'] =='1':
            if config['scaleout_type_wrt_HW'] =='4':
                self.scale_up_BW_per_link_PEAK = (float(config["serdes_rate_Gbps"])*self.serdes_lane/self.byte)/2
            else:
                self.scale_up_BW_per_link_PEAK = (float(config["serdes_rate_Gbps"]) * self.serdes_lane / self.byte)
        else:
            self.scale_up_BW_per_link_PEAK = (float(config["serdes_rate_Gbps"]) * self.serdes_lane / self.byte)
        self.scale_up_BW_per_link_ACHIEVABLE =self.scale_up_BW_per_link_PEAK * self.fabric_efficiency
        #print(self.scale_up_BW_per_link_ACHIEVABLE)
        self.total_mdfi_BW =int(config["total_mdfi_BW"])

        #print(self.total_scale_up_BW)
        self.allreduce_algo = config["allreduce_algo"] #'a2a'#
        self.allgather_algo = config["allgather_algo"] #'a2a'#
        self.all_to_all_algo = config["all_to_all_algo"]
        self.cd_latency_ns = int(config["cd_latency_ns"])
        self.scale_up_link_latency_ns = int(config["scale_up_link_latency_ns"])
        self.scale_up_switch_latency_ns = int(config["scale_up_switch_latency_ns"])
        self.scale_up_no_sockets_within_group = int(config["scale_up_no_sockets_within_group"])
        self.scale_up_switch_levels = ( 1 if (self.nsockets/self.scale_up_no_sockets_within_group) < 1
                                        else (self.nsockets/self.scale_up_no_sockets_within_group))
        self.scale_up_latency_us_SWITCH = 3*(self.cd_latency_ns*2 +(self.scale_up_switch_latency_ns+
                                                                    self.scale_up_link_latency_ns*2)
                                             *self.scale_up_switch_levels)/1000
        self.scale_up_latency_us_GLUELESS = 3*(self.cd_latency_ns*2+self.scale_up_link_latency_ns)/1000
        # self.nGPUs_per_node = self.nsockets
        # self.boards_per_rack = int(config["boards_per_rack"])
        # self.nracks_in_system = int(config["nracks_in_system"])
        # self.nnodes_in_system = int(config["nnodes_in_system"])
        # self.nGPUs_in_system = self.nGPUs_per_node*self.nnodes_in_system
        # self.ntiles_in_system = self.nGPUs_in_system*self.tiles_per_card
        # self.nPVC_cards_per_host = int(config["nPVC_cards_per_host"])
        # self.nhosts_Xeon = int(config["nhosts_Xeon"])
        # self.nXeon_sockets_per_Host = int(config["nXeon_sockets_per_Host"])
        # self.ncores_per_socket = int(config["ncores_per_socket"])
        # self.nPCI_lanes_Xeon2PVC_per_Xeon = int(config["nPCI_lanes_Xeon2PVC_per_Xeon"])#Num of PCI (Gen 5) Lanes Xeon2PVC per Xeon (3x16)
        # self.nPCI_lanes_Xeon2NIC_per_Xeon = int(config["nPCI_lanes_Xeon2NIC_per_Xeon"])#of PCIe Lanes Xeon2NIC per Xeon(2x16)
        # self.scale_out_algorithm = config["scale_out_algorithm"]
        # self.scale_out_option = config["scale_out_option"]
        # self.PCIe_BW_R_or_W_only = 64*0.82 #PCIe BW for read or write only  (64GB/s for 128B payload @ 82% eff)
        # self.PCIe_BW_R_and_W = 64*0.71 #PCIe BW for both read and write (64GB/s for 128B payload @ 71% eff)
        # self.HFI_BW = 25*0.8 #HFI BW(25GB/s per link)
        # self.nHFIs_for_inter_node_reduction = int(config["nHFIs_for_inter_node_reduction"])
        # self.total_HFI_BW = self.HFI_BW*self.nHFIs_for_inter_node_reduction
        # self.NIC_latency_us = float(config["NIC_latency_us"])
        # self.PCIe_latency_us = float(config["PCIe_latency_us"])
        # self.total_scaleout_latency = self.NIC_latency_us+self.PCIe_latency_us
        # self.ethernet_fabric_BW =  float(config["ethernet_fabric_BW"])#Ethernet fabric BW(GB/s)
        # self.achievable_read_memBW = 105*0.8 #Achievable Read MemBW (GB/s) (105GB/s per socket on skx)- peak 125GB/s
        # self.achievable_write_memBW = 105*0.8 #Achievable Write MemBW (GB/s) (105 GB/s per socket on skx)
        # self.achievable_per_core_memBW = float(config["achievable_per_core_memBW"]) #Achievable Per core MemBW (GB/s) (20 GB/s per socket on skx)
        # self.percentage_cores_for_collectives = float(config["percentage_cores_for_collectives"])  #Percentage of cores dedicated to collectives(in single socket)
        # self.total_memBW_available_for_comms = (self.percentage_cores_for_collectives/100)*\
        #                                        self.achievable_per_core_memBW*self.ncores_per_socket*\
        #                                        self.nXeon_sockets_per_Host #Total MemBW available for comms(across multiple sockets)
        # self.nPCIe_slots = int(config["nPCIe_slots"])
        # self.total_PCIe_R_or_BW = self.PCIe_BW_R_or_W_only*self.nPCIe_slots
        # self.total_PCIe_R_and_BW = self.PCIe_BW_R_and_W*self.nPCIe_slots
        self.use_pipeline = int(config["use_pipeline"])
        self.arbitrarily_large_message_size = 512*1024*1024*1024
        if self.use_pipeline==0:
            self.latency_threshold_message_size_for_scale_out = self.arbitrarily_large_message_size
            self.latency_threshold_message_size_for_scale_up = self.arbitrarily_large_message_size
            self.latency_threshold_message_size_for_MDFI = self.arbitrarily_large_message_size
        else:
            #self.latency_threshold_message_size_for_scale_out = self.message_size / float(config["num_chunks"])
            self.latency_threshold_message_size_for_scale_out = 1*1024*1024
            #self.latency_threshold_message_size_for_scale_up = self.message_size / float(config["num_chunks"])
            self.latency_threshold_message_size_for_scale_up = 4000*1024*1024
            #self.latency_threshold_message_size_for_MDFI = self.message_size / float(config["num_chunks"])
            if config['scale_out_flag'] == '1':
                if config['scaleout_type_wrt_HW'] == '3':
                    self.latency_threshold_message_size_for_MDFI = 4000*1024*1024
                else:
                    self.latency_threshold_message_size_for_MDFI = 4*1024*1024
            else:
                self.latency_threshold_message_size_for_MDFI = 4*1024*1024

        self.num_chunks = max(1,self.message_size/self.latency_threshold_message_size_for_MDFI)
        self.xdim_3d_torus = 4
        self.ydim_3d_torus = 2
        self.zdim_3d_torus = 2
        self.memory_read_congestion_factor = float(config["memory_read_congestion_factor"])
        self.memory_write_congestion_factor = float(config["memory_write_congestion_factor"])
        self.L3_read_congestion_factor = float(config["L3_read_congestion_factor"])
        self.L3_write_congestion_factor = float(config["L3_write_congestion_factor"])
        self.max_achievable_read_memBW = self.max_achievable_read_memBW_no_congession * float(config["memory_read_congestion_factor"])
        self.max_achievable_write_memBW = self.max_achievable_write_memBW_no_congession * float(config["memory_write_congestion_factor"])
        self.achievable_read_L3_BW_with_congestion = float(config["L3_read_congestion_factor"])*self.read_memBW_per_dss
        self.achievable_write_L3_BW_with_congestion = float(
            config["L3_write_congestion_factor"]) * self.write_memBW_per_dss
        self.use_full_message_size_in_HBM_latency_calculation = int(config["use_full_message_size_in_HBM_latency_calculation"])
        self.use_chunk_size_in_MDFI_latency_calculation = int(
            config["use_chunk_size_in_MDFI_latency_calculation"])
        self.Total_Tiles_communicating_for_A2A = int(config["Total_Tiles_communicating_for_A2A"])
        self.mdfi_latency_us = 3*self.mdfi_link_latency/(self.frequency_in_Ghz*1000)
        self.other_latency_us = ((self.L3_read_cache_miss_for_data_from_remote_write+
                                                                          self.L3_read_cache_miss_on_sync_flag+self.thread_dispatch
                                                                          +self.L3_write_cache_hit_on_data+
                                                                          self.L3_write_cache_hit_on_sync_flag+
                                                                          self.L1_hit_per_cache_line)/(self.frequency_in_Ghz*1000))
        self.L3_hit_remotetile_on_same_package = 552
        self.total_mdfi_latency = min((self.mdfi_latency_us+self.other_latency_us),self.L3_hit_remotetile_on_same_package/(self.frequency_in_Ghz*1000))
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        self.L3_hit_between_P0T0_P1T0 = 1130
        self.total_scaleup_latency_us= min((self.other_latency_us+scale_up_latency_us+self.total_mdfi_latency),((self.L3_hit_between_P0T0_P1T0*1.5)/(self.frequency_in_Ghz*1000)+
                                                                              (self.mdfi_link_latency/2)/
                                                                              (self.frequency_in_Ghz*1000)))

        #initialize all output variable to zero
        self.final_mdfi_latency =0
        self.final_scale_up_latency =0
        self.final_local_read_mdfi =0
        self.final_local_read_scale_up =0
        self.final_local_write_scale_up =0
        self.final_remote_write_mdfi =0
        self.final_remote_write_scale_up =0
        self.final_mdfi_time_us =0
        self.final_scale_up_time_us =0
        self.final_total_time_us =0
        self.final_mdfi_achieved_BW =0
        self.final_scale_up_achieved_BW =0
        self.final_mdfi_latency_percentage =0
        self.final_mdfi_Local_R_W_sum_percentage =0
        self.final_mdfi_write_percentage =0
        self.final_percentage_peak_BW_mdfi =0
        self.final_scale_up_latency_percentage =0
        self.final_scale_up_local_R_W_sum_percentage =0
        self.final_scale_up_write_percentage =0
        self.final_percentage_peak_BW_scale_up =0
        self.final_scaleout_latency = 0
        self.final_local_read_scaleout = 0
        self.final_local_write_scaleout = 0
        self.final_remote_write_scaleout = 0
        self.final_total_scaleout_time_usec = 0
        self.final_scaleout_achived_BW = 0



    def allreduce(self):
        if self.allreduce_algo == 'tree':
            out = self.allreduce_tree()
        elif self.allreduce_algo == 'ring':
            out = self.allreduce_ring()
        elif self.allreduce_algo == 'bidir_ring':
            out = self.allreduce_bidir_ring()
        elif self.allreduce_algo == 'a2a':
            out = self.allreduce_a2a()
        elif self.allreduce_algo == 'hypercube':
            out = self.allreduce_hypercube()
        elif self.allreduce_algo == '3d_torus':
            out = self.allreduce_3d_torus()
        return out

    def allgather(self):
        if self.allgather_algo == 'tree':
            out = self.allgather_tree()
        elif self.allgather_algo == 'ring':
            out = self.allgather_ring()
        elif self.allgather_algo == 'bidir_ring':
            out = self.allgather_bidir_ring()
        elif self.allgather_algo == 'a2a':
            out = self.allgather_a2a()
        elif self.allgather_algo == 'hypercube':
            out = self.allgather_hypercube()
        elif self.allgather_algo == '3d_torus':
            out = self.allgather_3d_torus()
        return out

    def reduce_scatter(self):
        if self.allgather_algo == 'a2a':
            out = self.reduce_scatter_a2a()
        return out

    def reduce(self):
        if self.allgather_algo == 'a2a':
            out = self.reduce_a2a()
        return out

    def broadcast(self):
        if self.allgather_algo == 'a2a':
            out = self.reduce_a2a()
        return out

    def scatter(self):
        if self.allgather_algo == 'a2a':
            out = self.allgather_a2a()
        return out

    def gather(self):
        if self.allgather_algo == 'a2a':
            out = self.allgather_a2a()
        return out

    def all_to_all(self):
        if self.all_to_all_algo == 'a2a':
            out = self.all_to_all_a2a()
        return out

    def reduce_scatter_a2a(self):
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
            nLinks = self.no_of_links
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS
            if self.nsockets == 4:
                nLinks = 6
            else:
                nLinks = self.no_of_links - 1

        #print(nLinks)
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = (self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up))*(self.nsockets - 1)/self.nsockets
        nsteps_scaleup = 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets


        total_latency_for_scale_up = 1*nsteps_scaleup*self.total_scaleup_latency_us+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up =self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up) *1000000/(1*self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0 #msg_size_per_scale_up_per_tile * 1000000 / (self.nsockets*self.gigaconv)
        remote_write_scale_up  =1 * \
                                min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up) *\
                                1000000 / (
                1 * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(self.latency_threshold_message_size_for_scale_up)
        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI) / \
            #                              self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1

        total_latency_for_MDFI = 1 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)\
                            * 1000000 / (
                self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def reduce_a2a(self):
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
            nLinks = self.no_of_links
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS
            if self.nsockets == 4:
                nLinks = 6
            else:
                nLinks = self.no_of_links - 1

        #print(nLinks)
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = (self.message_size / (self.no_of_concurrent_messages_over_scale_up))
        nsteps_scaleup = 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets


        total_latency_for_scale_up = 1*nsteps_scaleup*self.total_scaleup_latency_us+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up =self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up) *1000000/(1*self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0 #msg_size_per_scale_up_per_tile * 1000000 / (self.nsockets*self.gigaconv)
        remote_write_scale_up  =1 * \
                                min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up) *\
                                1000000 / (
                1 * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(self.latency_threshold_message_size_for_scale_up)
        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI) / \
            #                              self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1

        total_latency_for_MDFI = 1 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)\
                            * 1000000 / (self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allreduce_tree(self):

        nLinks = self.no_of_links
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = self.message_size / (
                    self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up)
        nsteps_scaleup = math.log(self.nsockets,2)
        total_message_volume_bytes = 2 * math.log(self.nsockets,2) * msg_size_per_scale_up_per_tile

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 3 * (self.nsockets - 1) * \
                                            min(msg_size_per_scale_up_per_tile,
                                                self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                    self.nsockets * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 2 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                    self.nsockets * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)



        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)\
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                    self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        #print(scale_up_BW_per_link)
        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                      self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = total_message_volume_bytes/(self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                        self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                                   self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                    self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]


        return out

    def allreduce_3d_torus(self):

        if self.nsockets == 8:
            nLinks = 6
        else:
            nLinks = self.no_of_links
        #nLinks = self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = math.ceil(self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up))
        nsteps_scaleup = (max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)-1) *3
        total_message_volume_bytes = 2 * (max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)-1) * \
                                     msg_size_per_scale_up_per_tile / max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 3 * (self.nsockets - 1) * \
                                            min(msg_size_per_scale_up_per_tile,
                                                self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                                    self.nsockets * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        # remote_write_scale_up = 2 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
        #                                                  self.latency_threshold_message_size_for_scale_up) * 1000000 / (
        #                                 self.nsockets * self.gigaconv)

        remote_write_scale_up = 2* (self.xdim_3d_torus-1)/self.xdim_3d_torus*min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up)* 1000000 / (
                                         1* self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size, self.latency_threshold_message_size_for_MDFI) \
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        #print(scale_up_BW_per_link)
        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = total_message_volume_bytes\
                                          / (self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]


        return out

    def allreduce_hypercube(self):

        if self.nsockets == 8:
            nLinks = 6
        else:
            nLinks = self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min(self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up),self.latency_threshold_message_size_for_scale_up)
        nsteps_scaleup = math.log(self.nsockets, 2)
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 3 * (self.nsockets - 1) * \
                                            min(msg_size_per_scale_up_per_tile,
                                                self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                                    self.nsockets * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 2 * (self.nsockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                        self.nsockets * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size, self.latency_threshold_message_size_for_MDFI) \
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]


        return out

    def allreduce_ring(self):

        nLinks = 4#self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE*nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min((self.message_size/(self.tiles_per_card*
                                                                 self.no_of_concurrent_messages_over_scale_up))
                                             ,self.latency_threshold_message_size_for_scale_up)
        nsteps_scaleup = self.nsockets-1
        total_message_volume_bytes = 2* (self.nsockets-1) * msg_size_per_scale_up_per_tile/self.nsockets

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS


        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation==1:
            local_reduce_plus_gather_scale_up = 3*(self.nsockets-1)*min(msg_size_per_scale_up_per_tile,
                                                                    self.latency_threshold_message_size_for_scale_up)*\
                                            1000000/(self.nsockets*self.gigaconv)#
        else:
            local_reduce_plus_gather_scale_up =0
        local_write_scale_up = 0
        remote_write_scale_up = 2*nsteps_scaleup*min(msg_size_per_scale_up_per_tile,
                                                     self.latency_threshold_message_size_for_scale_up)*\
                                1000000/(self.nsockets*self.gigaconv)#
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)



        #-------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)

        try:
            #msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)/\
            #                             self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size/self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card-1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3* nsteps_MDFI*min(msg_size_per_MDFI_per_tile,
                                                           self.latency_threshold_message_size_for_MDFI)*1000000/\
                                        (self.tiles_per_card*self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2* nsteps_MDFI*min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)*\
                            1000000/(self.tiles_per_card*self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)



        #----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up


        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI/\
                                     min(self.no_of_dss_or_sms*self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)


        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up/ \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up/\
                                          min(self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)



        try:
            self.final_remote_write_mdfi = remote_write_MDFI/min(self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW,Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up/min((self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion),self.max_achievable_write_memBW
                                                ,min(self.no_of_dss_or_sms,nLinks)*scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency+self.final_local_read_mdfi+self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us+self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2* min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)*nsteps_MDFI/\
                                      (self.tiles_per_card*self.final_mdfi_time_us/1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2*(self.nsockets-1)*\
                                          msg_size_per_scale_up_per_tile\
                                          /(self.nsockets*self.final_scale_up_time_us/1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW*100/(self.total_mdfi_BW*self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency*100/self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (self.final_local_read_scale_up+self.final_local_write_scale_up)*\
                                                       100/self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up*100/self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW*100/(self.total_scale_up_BW*self.gigaconv)


        out =[self.final_mdfi_latency,self.final_scale_up_latency,self.final_local_read_mdfi,self.final_local_read_scale_up,self.final_local_write_scale_up,
              self.final_remote_write_mdfi,self.final_remote_write_scale_up,self.final_mdfi_time_us,self.final_scale_up_time_us,self.final_total_time_us,
              self.final_mdfi_achieved_BW,self.final_scale_up_achieved_BW,self.final_mdfi_latency_percentage,self.final_mdfi_Local_R_W_sum_percentage,
              self.final_mdfi_write_percentage,self.final_percentage_peak_BW_mdfi,self.final_scale_up_latency_percentage,self.final_scale_up_local_R_W_sum_percentage,
              self.final_scale_up_write_percentage,self.final_percentage_peak_BW_scale_up]



        return out

    def allreduce_bidir_ring(self):

        nLinks = 4#self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE*nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min((self.message_size/(self.tiles_per_card*
                                                                 self.no_of_concurrent_messages_over_scale_up))
                                             ,self.latency_threshold_message_size_for_scale_up)/2
        nsteps_scaleup = self.nsockets-1
        total_message_volume_bytes = 2* (self.nsockets-1) * msg_size_per_scale_up_per_tile/self.nsockets

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS


        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation==1:
            local_reduce_plus_gather_scale_up = 3*(self.nsockets-1)*min(msg_size_per_scale_up_per_tile,
                                                                    self.latency_threshold_message_size_for_scale_up)*\
                                            1000000/(self.nsockets*self.gigaconv)#
        else:
            local_reduce_plus_gather_scale_up =0
        local_write_scale_up = 0
        remote_write_scale_up = 2*nsteps_scaleup*min(msg_size_per_scale_up_per_tile,
                                                     self.latency_threshold_message_size_for_scale_up)*\
                                1000000/(self.nsockets*self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)



        #-------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)

        try:
            #msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)/\
            #                             self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size/self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card-1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3* nsteps_MDFI*min(msg_size_per_MDFI_per_tile,
                                                           self.latency_threshold_message_size_for_MDFI)*1000000/\
                                        (self.tiles_per_card*self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2* nsteps_MDFI*min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)*\
                            1000000/(self.tiles_per_card*self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)



        #----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up


        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI/\
                                     min(self.no_of_dss_or_sms*self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)


        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up/ \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up/\
                                          min(self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)



        try:
            self.final_remote_write_mdfi = remote_write_MDFI/min(self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW,Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up/min((self.no_of_dss_or_sms*self.achievable_write_L3_BW_with_congestion),self.max_achievable_write_memBW
                                                ,min(self.no_of_dss_or_sms,nLinks)*scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency+self.final_local_read_mdfi+self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us+self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2* min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)*nsteps_MDFI/\
                                      (self.tiles_per_card*self.final_mdfi_time_us/1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2*(self.nsockets-1)*\
                                          msg_size_per_scale_up_per_tile\
                                          /(self.nsockets*self.final_scale_up_time_us/1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi*100/self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW*100/(self.total_mdfi_BW*self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency*100/self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (self.final_local_read_scale_up+self.final_local_write_scale_up)*\
                                                       100/self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up*100/self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW*100/(self.total_scale_up_BW*self.gigaconv)


        out =[self.final_mdfi_latency,self.final_scale_up_latency,self.final_local_read_mdfi,self.final_local_read_scale_up,self.final_local_write_scale_up,
              self.final_remote_write_mdfi,self.final_remote_write_scale_up,self.final_mdfi_time_us,self.final_scale_up_time_us,self.final_total_time_us,
              self.final_mdfi_achieved_BW,self.final_scale_up_achieved_BW,self.final_mdfi_latency_percentage,self.final_mdfi_Local_R_W_sum_percentage,
              self.final_mdfi_write_percentage,self.final_percentage_peak_BW_mdfi,self.final_scale_up_latency_percentage,self.final_scale_up_local_R_W_sum_percentage,
              self.final_scale_up_write_percentage,self.final_percentage_peak_BW_scale_up]



        return out

    def allreduce_a2a(self):
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
            nLinks = self.no_of_links
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS
            if self.nsockets == 4:
                nLinks = 6
            else:
                nLinks = self.no_of_links - 1

        #print(nLinks)
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min((self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up)),
                                             self.latency_threshold_message_size_for_scale_up)*(self.nsockets - 1)/self.nsockets
        nsteps_scaleup = 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets



        total_latency_for_scale_up = 2*nsteps_scaleup*self.total_scaleup_latency_us+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up =self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up) *1000000/(1*self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0 #msg_size_per_scale_up_per_tile * 1000000 / (self.nsockets*self.gigaconv)
        remote_write_scale_up  =2 * \
                                min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up) *\
                                1000000 / (
                1 * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(self.latency_threshold_message_size_for_scale_up)
        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI) / \
            #                              self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1

        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)\
                            * 1000000 / (
                self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_tree(self):
        nLinks = self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up)
        nsteps_scaleup = math.log(self.nsockets, 2)
        total_message_volume_bytes = 2 * math.log(self.nsockets, 2) * msg_size_per_scale_up_per_tile

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2 * nsteps_scaleup * (self.other_latency_us
                                                           + scale_up_latency_us) + self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1 * (self.nsockets - 1) * \
                                                min(msg_size_per_scale_up_per_tile,
                                                    self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                                        self.nsockets * self.gigaconv) #(1 *) because of just allgather
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 1 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                        self.nsockets * self.gigaconv) #(1 *) because of just allgather
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)\
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                    self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        # print(scale_up_BW_per_link)
        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = total_message_volume_bytes / (self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_3d_torus(self):
        if self.nsockets == 8:
            nLinks = 6
        else:
            nLinks = self.no_of_links
        #nLinks = self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = math.ceil(self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up))
        nsteps_scaleup = (max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)-1) *3
        total_message_volume_bytes = 2 * (max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)-1) * \
                                     msg_size_per_scale_up_per_tile / max(self.xdim_3d_torus,self.ydim_3d_torus,self.zdim_3d_torus)

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1 * (self.nsockets - 1) * \
                                            min(msg_size_per_scale_up_per_tile,
                                                self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                                    self.nsockets * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        # remote_write_scale_up = 2 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
        #                                                  self.latency_threshold_message_size_for_scale_up) * 1000000 / (
        #                                 self.nsockets * self.gigaconv)

        remote_write_scale_up = 1* (self.xdim_3d_torus-1)/self.xdim_3d_torus*min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up)* 1000000 / (
                                         1* self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size, self.latency_threshold_message_size_for_MDFI) \
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        #print(scale_up_BW_per_link)
        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = total_message_volume_bytes\
                                          / (self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_hypercube(self):
        if self.nsockets == 8:
            nLinks = 6
        else:
            nLinks = self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min(self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up),self.latency_threshold_message_size_for_scale_up)
        nsteps_scaleup = math.log(self.nsockets, 2)
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1 * (self.nsockets - 1) * \
                                            min(msg_size_per_scale_up_per_tile,
                                                self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                                    self.nsockets * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 1 * (self.nsockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * 1000000 / (
                                        self.nsockets * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size, self.latency_threshold_message_size_for_MDFI) \
            #                              / self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_ring(self):
        nLinks = 4  # self.no_of_links
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min((self.message_size / (self.tiles_per_card *
                                                                   self.no_of_concurrent_messages_over_scale_up))
                                             , self.latency_threshold_message_size_for_scale_up)
        nsteps_scaleup = self.nsockets - 1

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2 * nsteps_scaleup * (self.other_latency_us
                                                           + scale_up_latency_us) + self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1 * (self.nsockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                              self.latency_threshold_message_size_for_scale_up) * \
                                                1000000 / (self.nsockets * self.gigaconv)  #
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 1 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * \
                                1000000 / (self.nsockets * self.gigaconv)  #
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)

        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)/\
            #                             self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / \
                                            (self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * \
                            1000000 / (self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion),
            self.max_achievable_write_memBW,
            min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                        self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                                   self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                    self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_bidir_ring(self):
        nLinks = 4  # self.no_of_links
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = min((self.message_size / (self.tiles_per_card *
                                                                   self.no_of_concurrent_messages_over_scale_up))
                                             , self.latency_threshold_message_size_for_scale_up) / 2
        nsteps_scaleup = self.nsockets - 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets

        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS

        total_latency_for_scale_up = 2 * nsteps_scaleup * (self.other_latency_us
                                                           + scale_up_latency_us) + self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1 * (self.nsockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                              self.latency_threshold_message_size_for_scale_up) * \
                                                1000000 / (self.nsockets * self.gigaconv)  #
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0
        remote_write_scale_up = 1 * nsteps_scaleup * min(msg_size_per_scale_up_per_tile,
                                                         self.latency_threshold_message_size_for_scale_up) * \
                                1000000 / (self.nsockets * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)

        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI)/\
            #                             self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1
        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency

        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / \
                                            (self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * \
                            1000000 / (self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                        self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                                   self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                    self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def allgather_a2a(self):
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
            nLinks = self.no_of_links
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS
            if self.nsockets == 4:
                nLinks = 6
            else:
                nLinks = self.no_of_links - 1

        # print(nLinks)
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = (self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up)) * (
                                                     self.nsockets - 1) / self.nsockets
        nsteps_scaleup = 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets

        total_latency_for_scale_up = 1 * nsteps_scaleup * self.total_scaleup_latency_us+ self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up = 1*self.message_size / (
                    self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up) * 1000000 / (1 * self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0  # msg_size_per_scale_up_per_tile * 1000000 / (self.nsockets*self.gigaconv)
        remote_write_scale_up = 1 * \
                                min(msg_size_per_scale_up_per_tile, self.latency_threshold_message_size_for_scale_up) * \
                                1000000 / (
                                        1 * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        # print(self.latency_threshold_message_size_for_scale_up)
        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI) / \
            #                              self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.no_of_concurrent_messages_over_mdfi
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1

        total_latency_for_MDFI = 1 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                                  self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                                                    self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = 1 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) \
                            * 1000000 / (
                                    self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0

        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,
                                                  self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out

    def all_to_all_a2a(self):
        if self.scale_up_option == 'SWITCH':
            scale_up_latency_us = self.scale_up_latency_us_SWITCH
            nLinks = self.no_of_links
        else:
            scale_up_latency_us = self.scale_up_latency_us_GLUELESS
            if self.nsockets == 4:
                nLinks = 6
            else:
                nLinks = self.no_of_links - 1

        #print(self.nsockets)
        effective_scale_up_BW = self.scale_up_BW_per_link_ACHIEVABLE * nLinks
        scale_up_BW_per_link = self.scale_up_BW_per_link_ACHIEVABLE
        msg_size_per_scale_up_per_tile = self.message_size *(self.nsockets - 1)/self.Total_Tiles_communicating_for_A2A
        nsteps_scaleup = 1
        total_message_volume_bytes = 2 * (self.nsockets - 1) * msg_size_per_scale_up_per_tile / self.nsockets


        total_latency_for_scale_up = 2*nsteps_scaleup*(self.other_latency_us
                                                       +scale_up_latency_us)+self.sw_latency_in_us

        if self.use_full_message_size_in_HBM_latency_calculation == 1:
            local_reduce_plus_gather_scale_up =self.message_size / (
                self.tiles_per_card * self.no_of_concurrent_messages_over_scale_up) *1000000/(1*self.gigaconv)
        else:
            local_reduce_plus_gather_scale_up = 0
        local_write_scale_up = 0 #msg_size_per_scale_up_per_tile * 1000000 / (self.nsockets*self.gigaconv)
        remote_write_scale_up  =min(msg_size_per_scale_up_per_tile,self.latency_threshold_message_size_for_scale_up) *\
                                1000000 / (
                1 * self.gigaconv)
        self.total_scale_up_BW = nLinks * self.scale_up_BW_per_link_ACHIEVABLE

        #print(self.latency_threshold_message_size_for_scale_up)
        # print(nLinks)
        # print(effective_scale_up_BW)
        # print(scale_up_BW_per_link)
        # print(msg_size_per_scale_up_per_tile)
        # print(nsteps_scaleup)
        # print(total_message_volume_bytes)
        # print(total_latency_for_scale_up)
        # print(local_reduce_plus_gather_scale_up)
        # print(local_write_scale_up)
        # print(remote_write_scale_up)

        # -------------------------------------
        Effective_remote_write_BW_over_MDFI = min(self.max_achievable_write_memBW,
                                                  self.mdfi_BW_per_tile_ACHIEVABLE)
        try:
            # msg_size_per_MDFI_per_tile = min(self.message_size,self.latency_threshold_message_size_for_MDFI) / \
            #                              self.no_of_concurrent_messages_over_mdfi
            msg_size_per_MDFI_per_tile = self.message_size / self.Total_Tiles_communicating_for_A2A
        except ZeroDivisionError:
            msg_size_per_MDFI_per_tile = 0

        nsteps_MDFI = self.tiles_per_card - 1

        total_latency_for_MDFI = 2 * nsteps_MDFI * self.total_mdfi_latency
        if self.use_chunk_size_in_MDFI_latency_calculation == 1:
            local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              self.latency_threshold_message_size_for_MDFI) * 1000000 / (
                self.tiles_per_card * self.gigaconv)
        else:
            local_reduce_plus_gather_MDFI = 0
        remote_write_MDFI = nsteps_MDFI * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI)\
                            * 1000000 / (
                self.tiles_per_card * self.gigaconv)

        # print(Effective_remote_write_BW_over_MDFI)
        # print(msg_size_per_MDFI_per_tile)
        # print(nsteps_MDFI)
        # print(total_latency_for_MDFI)
        # print(local_reduce_plus_gather_MDFI)
        # print(remote_write_MDFI)

        # ----------------------------------------

        self.final_mdfi_latency = total_latency_for_MDFI
        self.final_scale_up_latency = total_latency_for_scale_up

        self.final_local_read_mdfi = local_reduce_plus_gather_MDFI / \
                                     min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                         self.max_achievable_read_memBW)

        self.final_local_read_scale_up = local_reduce_plus_gather_scale_up / \
                                         min(self.no_of_dss_or_sms * self.achievable_read_L3_BW_with_congestion,
                                             self.max_achievable_read_memBW)

        self.final_local_write_scale_up = local_write_scale_up / \
                                          min(self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                                              self.max_achievable_read_memBW)

        try:
            self.final_remote_write_mdfi = remote_write_MDFI / min(
                self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion,
                self.max_achievable_read_memBW, Effective_remote_write_BW_over_MDFI)
        except ZeroDivisionError:
            self.final_remote_write_mdfi = 0


        self.final_remote_write_scale_up = remote_write_scale_up / min(
            (self.no_of_dss_or_sms * self.achievable_write_L3_BW_with_congestion), self.max_achievable_write_memBW
            , min(self.no_of_dss_or_sms, nLinks) * scale_up_BW_per_link)

        self.final_mdfi_time_us = self.final_mdfi_latency + self.final_local_read_mdfi + self.final_remote_write_mdfi

        if self.nsockets != 1:
            self.final_scale_up_time_us = self.final_scale_up_latency + self.final_local_read_scale_up + \
                                          self.final_local_write_scale_up + self.final_remote_write_scale_up
        else:
            self.final_scale_up_time_us = 0

        self.final_total_time_us = self.final_mdfi_time_us + self.final_scale_up_time_us

        try:
            self.final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile,self.latency_threshold_message_size_for_MDFI) * nsteps_MDFI / \
                                          (self.tiles_per_card * self.final_mdfi_time_us / 1000000)
        except ZeroDivisionError:
            self.final_mdfi_achieved_BW = 0

        self.final_scale_up_achieved_BW = 2 * (self.nsockets - 1) * \
                                          msg_size_per_scale_up_per_tile \
                                          / (self.nsockets * self.final_scale_up_time_us / 1000000)

        try:
            self.final_mdfi_latency_percentage = self.final_mdfi_latency * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_latency_percentage = 0

        try:
            self.final_mdfi_Local_R_W_sum_percentage = self.final_local_read_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_Local_R_W_sum_percentage = 0

        try:
            self.final_mdfi_write_percentage = self.final_remote_write_mdfi * 100 / self.final_mdfi_time_us
        except ZeroDivisionError:
            self.final_mdfi_write_percentage = 0

        try:
            self.final_percentage_peak_BW_mdfi = self.final_mdfi_achieved_BW * 100 / (
                    self.total_mdfi_BW * self.gigaconv)
        except ZeroDivisionError:
            self.final_percentage_peak_BW_mdfi = 0

        self.final_scale_up_latency_percentage = self.final_scale_up_latency * 100 / self.final_scale_up_time_us

        self.final_scale_up_local_R_W_sum_percentage = (
                                                               self.final_local_read_scale_up + self.final_local_write_scale_up) * \
                                                       100 / self.final_scale_up_time_us

        self.final_scale_up_write_percentage = self.final_remote_write_scale_up * 100 / self.final_scale_up_time_us

        self.final_percentage_peak_BW_scale_up = self.final_scale_up_achieved_BW * 100 / (
                self.total_scale_up_BW * self.gigaconv)

        out = [self.final_mdfi_latency, self.final_scale_up_latency, self.final_local_read_mdfi,
               self.final_local_read_scale_up, self.final_local_write_scale_up,
               self.final_remote_write_mdfi, self.final_remote_write_scale_up, self.final_mdfi_time_us,
               self.final_scale_up_time_us, self.final_total_time_us,
               self.final_mdfi_achieved_BW, self.final_scale_up_achieved_BW, self.final_mdfi_latency_percentage,
               self.final_mdfi_Local_R_W_sum_percentage,
               self.final_mdfi_write_percentage, self.final_percentage_peak_BW_mdfi,
               self.final_scale_up_latency_percentage, self.final_scale_up_local_R_W_sum_percentage,
               self.final_scale_up_write_percentage, self.final_percentage_peak_BW_scale_up]
        return out


    # def scaleout(self):
    #     if self.scale_out_algorithm == 'tree':
    #         scaleout_out = self.scaleout_tree()
    #     elif self.scale_out_algorithm == 'ring':
    #         scaleout_out = self.scaleout_ring()
    #     elif self.scale_out_algorithm == 'a2a':
    #         scaleout_out = self.scaleout_a2a()
    #     return scaleout_out
    #
    # def scaleout_ring(self):
    #     self.msg_size_per_tile = self.message_size/self.tiles_per_card
    #     self.nsteps_scaleout = self.nnodes_in_system-1
    #     self.total_msg_volume = 2*self.nsteps_scaleout*self.msg_size_per_tile/self.nnodes_in_system
    #     time_to_go_over_PCIe = (min(self.msg_size_per_tile,self.latency_threshold_message_size_for_scale_out*2)/
    #                             self.total_PCIe_R_or_BW)/1000 #(self.message_size/self.total_PCIe_R_or_BW)/1000
    #     time_to_go_over_HFI = (min(self.msg_size_per_tile,self.latency_threshold_message_size_for_scale_out*2)/
    #                             self.total_HFI_BW)/1000 #(self.message_size / self.total_HFI_BW) / 1000
    #     time_to_go_over_ethernet = (self.message_size / self.ethernet_fabric_BW) / 1000
    #     print(self.msg_size_per_tile)
    #     print(self.nsteps_scaleout)
    #     print(self.total_msg_volume)
    #     print(time_to_go_over_PCIe)
    #     print(time_to_go_over_HFI)
    #     print(time_to_go_over_ethernet)
    #
    #     self.total_latency_scaleout = 2*self.nsteps_scaleout*(self.total_scaleout_latency+time_to_go_over_HFI
    #                                                           +time_to_go_over_PCIe)
    #     self.local_reduce_plus_gather_scaleout = 3*self.nsteps_scaleout*\
    #                                              min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     self.local_write_scaleout = 0
    #     self.remote_write_scaleout = 2*self.nsteps_scaleout*\
    #                                              min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     #print(self.total_HFI_BW)
    #     self.final_scaleout_latency = self.total_latency_scaleout
    #     self.final_local_read_scaleout = self.local_reduce_plus_gather_scaleout/\
    #                                      min(self.no_of_dss_or_sms*self.read_memBW_per_dss,self.max_achievable_read_memBW)
    #     self.final_local_write_scaleout = self.local_write_scaleout/((self.final_scale_up_local_R_W_sum_percentage
    #                                                                  *self.write_memBW_per_dss/
    #                                                                  100) if (self.final_scale_up_local_R_W_sum_percentage*
    #                                                                            self.write_memBW_per_dss/100)
    #                                                                           < self.max_achievable_read_memBW else self.max_achievable_read_memBW)
    #     self.final_remote_write_scaleout = self.remote_write_scaleout/min(min(self.no_of_dss_or_sms*self.write_memBW_per_dss,
    #                                                                           self.max_achievable_write_memBW),
    #                                                                       min(self.total_PCIe_R_and_BW,self.total_HFI_BW))
    #     self.final_total_scaleout_time_usec = self.final_scaleout_latency+self.final_local_read_scaleout+\
    #                                           self.final_remote_write_scaleout
    #     self.final_scaleout_achived_BW = 2*(self.nnodes_in_system-1)*self.msg_size_per_tile/\
    #                                      (self.nnodes_in_system*self.final_total_scaleout_time_usec/1000000)
    #
    #     scaleout_out = [self.final_scaleout_latency,self.final_local_read_scaleout,self.final_local_write_scaleout,
    #                     self.final_remote_write_scaleout,self.final_total_scaleout_time_usec,self.final_scaleout_achived_BW]
    #
    #     return scaleout_out
    #
    # def scaleout_tree(self):
    #     self.msg_size_per_tile = self.message_size
    #     self.nsteps_scaleout = math.log(self.nnodes_in_system,2)
    #     self.total_msg_volume = 2*self.nsteps_scaleout*self.msg_size_per_tile/self.nnodes_in_system
    #     time_to_go_over_PCIe = (self.msg_size_per_tile/self.PCIe_BW_R_or_W_only)/1000
    #     time_to_go_over_HFI = (self.msg_size_per_tile/ self.total_HFI_BW) / 1000
    #     time_to_go_over_ethernet = (self.msg_size_per_tile/ self.ethernet_fabric_BW) / 1000
    #     self.total_latency_scaleout = 2*self.nsteps_scaleout*self.total_scaleout_latency
    #     self.local_reduce_plus_gather_scaleout = 3*self.nsteps_scaleout*\
    #                                              min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     self.local_write_scaleout = 0
    #     self.remote_write_scaleout = 2*self.nsteps_scaleout*\
    #                                              min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     self.final_scaleout_latency = self.total_latency_scaleout
    #     self.final_local_read_scaleout = self.local_reduce_plus_gather_scaleout/\
    #                                      min(self.no_of_dss_or_sms*self.read_memBW_per_dss,self.max_achievable_read_memBW)
    #     self.final_local_write_scaleout = self.local_write_scaleout/((self.final_scale_up_local_R_W_sum_percentage
    #                                                                  *self.write_memBW_per_dss/
    #                                                                  100) if (self.final_scale_up_local_R_W_sum_percentage*
    #                                                                            self.write_memBW_per_dss/100)
    #                                                                           < self.max_achievable_read_memBW else self.max_achievable_read_memBW)
    #     self.final_remote_write_scaleout = self.remote_write_scaleout/min(min(self.no_of_dss_or_sms*self.write_memBW_per_dss,
    #                                                                           self.max_achievable_write_memBW),
    #                                                                       min(self.total_PCIe_R_and_BW,self.total_HFI_BW))
    #     self.final_total_scaleout_time_usec = self.final_scaleout_latency+self.final_local_read_scaleout+\
    #                                           self.final_remote_write_scaleout
    #     self.final_scaleout_achived_BW = 2*(self.nnodes_in_system-1)*self.msg_size_per_tile/\
    #                                      (self.nnodes_in_system*self.final_total_scaleout_time_usec/1000000)
    #     print(self.msg_size_per_tile)
    #
    #     scaleout_out = [self.final_scaleout_latency,self.final_local_read_scaleout,self.final_local_write_scaleout,
    #                     self.final_remote_write_scaleout,self.final_total_scaleout_time_usec,self.final_scaleout_achived_BW]
    #
    #     return scaleout_out
    #
    # def scaleout_a2a(self):
    #     self.msg_size_per_tile = self.message_size
    #     self.nsteps_scaleout = 1
    #     self.total_msg_volume = 2*self.nsteps_scaleout*self.msg_size_per_tile/self.nnodes_in_system
    #     time_to_go_over_PCIe = (self.msg_size_per_tile/self.PCIe_BW_R_or_W_only)/1000
    #     time_to_go_over_HFI = (self.msg_size_per_tile/ self.total_HFI_BW) / 1000
    #     time_to_go_over_ethernet = (self.msg_size_per_tile/ self.ethernet_fabric_BW) / 1000
    #     self.total_latency_scaleout = 2*self.nsteps_scaleout*self.total_scaleout_latency
    #     self.local_reduce_plus_gather_scaleout = min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/self.gigaconv
    #     self.local_write_scaleout = min(self.msg_size_per_tile,
    #                                                  self.latency_threshold_message_size_for_scale_out)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     print(self.local_write_scaleout)
    #     self.remote_write_scaleout = 2*(self.nnodes_in_system-1)*1000000/\
    #                                              (self.nnodes_in_system*self.gigaconv)
    #     self.final_scaleout_latency = self.total_latency_scaleout
    #     self.final_local_read_scaleout = self.local_reduce_plus_gather_scaleout/\
    #                                      min(self.no_of_dss_or_sms*self.read_memBW_per_dss,self.max_achievable_read_memBW)
    #     self.final_local_write_scaleout = self.local_write_scaleout/((self.final_scale_up_local_R_W_sum_percentage
    #                                                                  *self.write_memBW_per_dss/
    #                                                                  100) if (self.final_scale_up_local_R_W_sum_percentage*
    #                                                                            self.write_memBW_per_dss/100)
    #                                                                           < self.max_achievable_read_memBW else self.max_achievable_read_memBW)
    #     self.final_remote_write_scaleout = self.remote_write_scaleout/min(min(self.no_of_dss_or_sms*self.write_memBW_per_dss,
    #                                                                           self.max_achievable_write_memBW),
    #                                                                       min(self.total_PCIe_R_and_BW,self.total_HFI_BW))
    #     self.final_total_scaleout_time_usec = self.final_scaleout_latency+self.final_local_read_scaleout+\
    #                                           self.final_remote_write_scaleout
    #     self.final_scaleout_achived_BW = 2*(self.nnodes_in_system-1)*self.msg_size_per_tile/\
    #                                      (self.nnodes_in_system*self.final_total_scaleout_time_usec/1000000)
    #
    #     scaleout_out = [self.final_scaleout_latency,self.final_local_read_scaleout,self.final_local_write_scaleout,
    #                     self.final_remote_write_scaleout,self.final_total_scaleout_time_usec,self.final_scaleout_achived_BW]
    #
    #     return scaleout_out
    #
    # def scaleout_flat(self):
    #     Latency_time_us = self.total_latency_us_scaleout*self.num_steps
    #     BW_time_us = (self.num_host-1)/self.num_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
    #     Gamma_term_us = 2*self.PCIe_chunk_size/self.PCIe_BW_GB_per_s_Read_and_Write*0.001
    #     total_time_us=Latency_time_us+BW_time_us+Gamma_term_us
    #
    #     return total_time_us
    #
    # def scaleout_2tft(self):
    #     if self.num_steps<=3:
    #         Latency_time_us = self.total_latency_us_scaleout*self.num_steps
    #         BW_time_us = (self.num_host-1)/self.num_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
    #         Gamma_term_us = 2*self.PCIe_chunk_size/self.PCIe_BW_GB_per_s_Read_and_Write*0.001
    #         total_time_us=Latency_time_us+BW_time_us+Gamma_term_us
    #     else:
    #         Num_steps_in_1st_tier = math.log(self.num_hosts_in_1st_tier,2)
    #         Num_steps_in_2nd_tier =self.num_steps-Num_steps_in_1st_tier
    #         Num_bytes_in_first_tier = self.scale_out_msg_size*(pow(2,Num_steps_in_1st_tier)-1)/pow(2,Num_steps_in_1st_tier)
    #         Num_bytes_in_second_tier = self.scale_out_msg_size*(pow(2,Num_steps_in_2nd_tier)-1)/self.num_host
    #         BW_term_us_1st_tier = Num_bytes_in_first_tier/(self.BW_multiplier_in_1st_tier*self.Total_inter_host_BW_GB_per_s)*0.001
    #         BW_term_us_2nd_tier =Num_bytes_in_second_tier/(self.BW_multiplier_in_2nd_tier*self.Total_inter_host_BW_GB_per_s)*0.001
    #         BW_Term_us_total =BW_term_us_1st_tier+BW_term_us_2nd_tier
    #         Latency_time_us = self.total_latency_us_scaleout * self.num_steps
    #         Gamma_term_us = 2 * self.PCIe_chunk_size / self.PCIe_BW_GB_per_s_Read_and_Write * 0.001
    #         total_time_us =BW_Term_us_total+Latency_time_us+Gamma_term_us
    #
    #     return total_time_us
    #
    # def scaleout_cafe(self):
    #     steps = self.num_host-1
    #     Latency_time_us = steps*self.scale_up_latency_cafe
    #     BW_time_us = (self.num_host-1)/self.num_host*self.scale_out_msg_size/self.Total_BW_per_RING_direction*0.001
    #     total_time_us=Latency_time_us+BW_time_us
    #
    #     return total_time_us

class Comms_scaleout():
    def __init__(self,config):
        # scaleout section

        self.scale_out_allreduce_algo = config["scale_out_allreduce_algo"]
        self.scale_out_latency = float(config["scale_out_latency"])
        self.host_involvement = float(config["host_involvement"])
        self.total_latency_us_scaleout = self.scale_out_latency + self.host_involvement
        self.scale_out_msg_size = float(config["scale_out_msg_size"])
        self.num_NICs = float(config["num_NICs"])
        self.BW_per_NIC_unidir_Gbps = float(config["BW_per_NIC_unidir_Gbps"])
        self.nic_efficiency = float(config["nic_efficiency"])
        self.Total_inter_host_BW_GB_per_s = self.num_NICs * self.BW_per_NIC_unidir_Gbps / 8 * self.nic_efficiency
        self.num_tiers_in_fat_tree = float(config["num_tiers_in_fat_tree"])
        self.num_switches_in_1st_tier = float(config["num_switches_in_1st_tier"])
        self.num_switches_in_2nd_tier = float(config["num_switches_in_2nd_tier"])
        self.num_hosts_in_1st_tier = float(config["num_hosts_in_1st_tier"])
        self.num_ports_in_each_switch = float(config["num_ports_in_each_switch"])
        self.num_ports_used_in_1st_tier = float(config["num_ports_used_in_1st_tier"])
        self.num_ports_used_in_2nd_tier = float(config["num_ports_used_in_2nd_tier"])
        self.BW_multiplier_in_1st_tier = self.num_ports_used_in_1st_tier / self.num_ports_in_each_switch
        self.BW_multiplier_in_2nd_tier = self.num_ports_used_in_2nd_tier / self.num_ports_in_each_switch
        self.PCIe_BW_GB_per_s_Read_and_Write = float(config["PCIe_BW_GB_per_s_Read_and_Write"])
        self.PCIe_chunk_size = 1 * 1024 * 1024
        self.num_tiles_per_pvc = float(config["num_tiles_per_pvc"]) #2
        self.num_pvc = float(config["num_pvc"]) #256
        self.num_PVC_per_host = float(config["num_PVC_per_host"]) #8
        self.num_tile_per_host = self.num_tiles_per_pvc * self.num_PVC_per_host
        self.total_num_tiles = self.num_tiles_per_pvc * self.num_pvc
        self.num_Tiles_involved_in_comms = self.total_num_tiles / self.num_tiles_per_pvc
        self.num_host = (round((self.num_pvc / self.num_PVC_per_host), 0))
        self.num_steps = math.log(self.num_host, 2)
        self.scaleout_type = config["scaleout_type"]
        self.scale_up_latency_cafe = float(config["scale_up_latency_cafe"])
        self.Total_num_of_available_links_cafe = float(config["Total_num_of_available_links_cafe"])
        self.BW_per_link_GB_per_s_cafe = float(config["BW_per_link_GB_per_s_cafe"])
        self.Total_BW_per_RING_direction = self.Total_num_of_available_links_cafe / 2 * self.BW_per_link_GB_per_s_cafe * 0.8
        # 1: H_2Tile_Nic_H
        # 2: H_2Tile_S_plus_N
        # 3: F_2Tile_N
        # 4: F_2Tile_Mixed
        # 5: H_1Tile_S_plus_N
        # 6: F_1Tile_N
        # 7: switch
        self.approach_type  = int(config['scaleout_type_wrt_HW'])
        self.Gamma_term_us =0
        self.data_parallel_with_model_split = int(config['data_parallel_with_model_split'])
        self.total_Xe_bw_GBps = (int(config['total_Xe_bw_GBps']))


    def scaleout(self):
        if self.scaleout_type == 'flat':
            scaleout_out = self.scaleout_flat()
        elif self.scaleout_type == '2tft':
            scaleout_out = self.scaleout_2tft()
        elif self.scaleout_type == 'cafe':
            scaleout_out = self.scaleout_cafe()
        elif self.scaleout_type == 'flat_a2a':
            scaleout_out = self.scaleout_flat_a2a()
        return scaleout_out

    def scaleout_flat(self):
        Latency_time_us = self.total_latency_us_scaleout*self.num_steps
        tiles_per_nic = self.num_tile_per_host / self.num_NICs


        if self.approach_type==1:
            if self.data_parallel_with_model_split==1:
                BW_time_us = 2 * (
                            self.num_host - 1) / self.num_host * tiles_per_nic * self.scale_out_msg_size / \
                             (self.Total_inter_host_BW_GB_per_s/self.num_NICs) * 0.001
            elif self.data_parallel_with_model_split==2:
                BW_time_us = 2 * (self.num_host - 1) / self.num_host * tiles_per_nic * (
                        self.scale_out_msg_size / self.num_tile_per_host) / (
                                         self.Total_inter_host_BW_GB_per_s / self.num_NICs) * 0.001
            elif self.data_parallel_with_model_split==3:
                BW_time_us = tiles_per_nic * self.scale_out_msg_size / \
                             (self.Total_inter_host_BW_GB_per_s / self.num_NICs) * 0.001
            else:
                BW_time_us = 2 * (self.num_host - 1) / self.num_host *tiles_per_nic* (
                            self.scale_out_msg_size / self.num_tile_per_host) / (self.Total_inter_host_BW_GB_per_s/self.num_NICs) * 0.001
        elif self.approach_type==2:
            BW_time_us = 2*(self.num_host-1)/self.num_host/self.num_tile_per_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
        elif self.approach_type == 3:
            self.num_steps = math.log(self.total_num_tiles, 2)
            Latency_time_us = self.total_latency_us_scaleout * self.num_steps
            BW_time_us = 2*(self.num_Tiles_involved_in_comms - 1) / self.num_Tiles_involved_in_comms * (self.scale_out_msg_size/2) / self.Total_inter_host_BW_GB_per_s * 0.001
        elif self.approach_type==4:
            BW_time_us = 2*(self.num_host-1)/self.num_host/self.num_PVC_per_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
        elif self.approach_type==5:
            BW_time_us = 2*(self.num_host-1)/self.num_host/self.num_PVC_per_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
        elif self.approach_type==6:
            self.num_steps = math.log(self.num_pvc, 2)
            Latency_time_us = self.total_latency_us_scaleout * self.num_steps
            BW_time_us = 2*(self.num_pvc-1)/self.num_pvc*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
        elif self.approach_type==7:
            if self.data_parallel_with_model_split==1:
                BW_time_us = 2 * (
                            self.num_host - 1) / self.num_host * tiles_per_nic * self.scale_out_msg_size / \
                             (self.Total_inter_host_BW_GB_per_s/self.num_NICs) * 0.001
            elif self.data_parallel_with_model_split==3:
                BW_time_us = tiles_per_nic * self.scale_out_msg_size / \
                             (self.Total_inter_host_BW_GB_per_s / self.num_NICs) * 0.001
            else:
                BW_time_us = 2 * (self.num_host - 1) / self.num_host * (
                            self.scale_out_msg_size / self.num_tile_per_host) / self.total_Xe_bw_GBps * 0.001

        Gamma_term_us = self.Gamma_term_us #self.switch_latency_us #2*self.PCIe_chunk_size/self.PCIe_BW_GB_per_s_Read_and_Write*0.001
        #print(Gamma_term_us)
        total_time_us=Latency_time_us+BW_time_us+Gamma_term_us

        return total_time_us

    def scaleout_2tft(self):
        if self.num_steps<=3:
            Latency_time_us = self.total_latency_us_scaleout*self.num_steps
            BW_time_us = (self.num_host-1)/self.num_host*self.scale_out_msg_size/self.Total_inter_host_BW_GB_per_s*0.001
            Gamma_term_us = 2*self.PCIe_chunk_size/self.PCIe_BW_GB_per_s_Read_and_Write*0.001
            total_time_us=Latency_time_us+BW_time_us+Gamma_term_us
        else:
            Num_steps_in_1st_tier = math.log(self.num_hosts_in_1st_tier,2)
            Num_steps_in_2nd_tier =self.num_steps-Num_steps_in_1st_tier
            Num_bytes_in_first_tier = self.scale_out_msg_size*(pow(2,Num_steps_in_1st_tier)-1)/pow(2,Num_steps_in_1st_tier)
            Num_bytes_in_second_tier = self.scale_out_msg_size*(pow(2,Num_steps_in_2nd_tier)-1)/self.num_host
            BW_term_us_1st_tier = Num_bytes_in_first_tier/(self.BW_multiplier_in_1st_tier*self.Total_inter_host_BW_GB_per_s)*0.001
            BW_term_us_2nd_tier =Num_bytes_in_second_tier/(self.BW_multiplier_in_2nd_tier*self.Total_inter_host_BW_GB_per_s)*0.001
            BW_Term_us_total =BW_term_us_1st_tier+BW_term_us_2nd_tier
            Latency_time_us = self.total_latency_us_scaleout * self.num_steps
            Gamma_term_us = 2 * self.PCIe_chunk_size / self.PCIe_BW_GB_per_s_Read_and_Write * 0.001
            total_time_us =BW_Term_us_total+Latency_time_us+Gamma_term_us

        return total_time_us

    def scaleout_cafe(self):
        steps = self.num_host-1
        Latency_time_us = steps*self.scale_up_latency_cafe
        BW_time_us = (self.num_host-1)/self.num_host*self.scale_out_msg_size/self.Total_BW_per_RING_direction*0.001
        total_time_us=Latency_time_us+BW_time_us

        return total_time_us

    def scaleout_flat_a2a(self):
        Latency_time_us = self.total_latency_us_scaleout*self.num_steps
        BW_time_us = (((self.num_PVC_per_host*self.num_tiles_per_pvc*self.num_host)-self.num_PVC_per_host*self.num_tiles_per_pvc)
                      /(self.num_PVC_per_host*self.num_tiles_per_pvc*self.num_host))*self.scale_out_msg_size*\
                     (self.num_PVC_per_host*self.num_tiles_per_pvc)/self.Total_inter_host_BW_GB_per_s*0.001
        Gamma_term_us = 2*self.PCIe_chunk_size/self.PCIe_BW_GB_per_s_Read_and_Write*0.001
        total_time_us=Latency_time_us+BW_time_us+Gamma_term_us

        return total_time_us


class I_O_projection():
    def __init__(self, config):
        self.total_image_size_in_bytes = config["total_image_size_in_bytes"]
        self.num_instance = config["num_instance"]
        self.Nodes_per_instance = config["Nodes_per_instance"]
        self.Total_HFI_BW = config["Total_HFI_BW"]
        self.Host_peer_to_peer_bandwidth = config["Host_peer_to_peer_bandwidth"]
        self.PCIe_BW_per_s_Read_or_Write =config["PCIe_BW_per_s_Read_or_Write"]



    def calculate_io(self):
        Total_bytes_per_instance = self.total_image_size_in_bytes
        Total_bytes_for_all_n_instances = self.num_instance*Total_bytes_per_instance
        DAOS_BW = 35*1000000000000
        Time_for_n_instances_to_load_52GB_of_images_each_sec = Total_bytes_for_all_n_instances/DAOS_BW
        Time_to_bring_1_28_M_per_200_images_from_DAO_to_SPR_DDR_HFI = (self.total_image_size_in_bytes/
                                                                       self.Nodes_per_instance)/self.Total_HFI_BW
        Time_fo_1_SPR_host_to_copy_52GB_200_to_the_other_host_over_UPI = (self.total_image_size_in_bytes/
                                                                       self.Nodes_per_instance)/self.Host_peer_to_peer_bandwidth
        Time_to_read_1_28M_images_from_host_DDR_to_6_PVC_tiles_per_host_over_PCIe = (self.total_image_size_in_bytes/
                                                                       self.Nodes_per_instance)/(self.PCIe_BW_per_s_Read_or_Write/6)
        total_io_time = Time_for_n_instances_to_load_52GB_of_images_each_sec+\
                        Time_to_bring_1_28_M_per_200_images_from_DAO_to_SPR_DDR_HFI+\
                        Time_fo_1_SPR_host_to_copy_52GB_200_to_the_other_host_over_UPI+\
                        Time_to_read_1_28M_images_from_host_DDR_to_6_PVC_tiles_per_host_over_PCIe
        total_io_time_ms = total_io_time*1000

        return total_io_time_ms


class A21_scaleout():
    def __init__(self, config):
        self.scale_out_allreduce_algo = config["scale_out_allreduce_algo"]
        self.scale_out_msg_size = float(config["scale_out_msg_size"])
        self.MemRd_Latency = float(config["MemRd_Latency"])
        self.RTS_CTS_overhead = float(config["RTS_CTS_overhead"]) #RTS-CTS overhead for msgs sizes greater than MTU
        self.Time_to_send_back_acknowledgement = float(config["Time_to_send_back_acknowledgement"]) #Time to send back acknowledgement to the sender that msg has been received
        self.Bandwidth = float(config["Bandwidth"])
        self.Num_nodes_in_a_grp = float(config["Num_nodes_in_a_grp"])
        self.num_NICs = float(config["num_NICs"])
        self.Bandwidth_same_switch = self.num_NICs*float(config["BW_per_NIC_unidir_Gbps"])*float(config["nic_efficiency"])/8
        self.Bandwidth_same_group_across_switch = self.num_NICs*float(config["BW_per_NIC_unidir_Gbps"])*\
                                                  float(config["nic_efficiency"])/8
        self.Bandwidth_across_groups_per_node = 155*2*float(config["BW_per_NIC_unidir_Gbps"])/(2*self.Num_nodes_in_a_grp*8 )
        self.Num_Ranks = float(config["Num_Ranks"])
        self.Num_of_nodes_per_switch = float(config["Num_of_nodes_per_switch"])
        self.Num_of_switches = math.ceil(self.Num_Ranks/self.Num_of_nodes_per_switch)
        self.Num_grps = math.ceil(self.Num_Ranks/self.Num_nodes_in_a_grp)
        self.Number_of_ranks_inside_a_grp = float(config["Number_of_ranks_inside_a_grp"])
        self.Num_ranks_inside_a_switch = float(config["Num_ranks_inside_a_switch"])



    def calc_scaleout_time(self):
        Num_phases_total = math.ceil(math.log(self.Num_Ranks,2))
        Num_phases_Inside_switch = math.ceil(math.log(self.Num_ranks_inside_a_switch, 2))
        Num_phases_Inside_group = math.ceil(math.log(self.Number_of_ranks_inside_a_grp, 2))
        Num_phases_inside_grp_across_switches = Num_phases_Inside_group-Num_phases_Inside_switch
        Num_phases_across_grp = Num_phases_total-Num_phases_Inside_switch-Num_phases_inside_grp_across_switches
        Chunk_size_for_allgather = self.scale_out_msg_size/self.Num_Ranks
        Total_msg_size_in_Allgather = Chunk_size_for_allgather*self.Num_Ranks
        Closest_power_of_2 = int(pow(2, int(math.log(self.Num_Ranks, 2))))
        Num_of_nodes_not_participating_in_step2 = self.Num_Ranks-Closest_power_of_2
        Min_number_of_nodes_participating_in_step2 = self.Num_nodes_in_a_grp/2
        unknown_array = np.array([71.48,25.93,11.97,6.21,3.23,1.48,0.59,0.3])
        unknown_DMA = 3650

        #Reduce scatter section
        #Step 1
        RS_Time_to_send_data_to_participating_ranks_in_the_same_group = Total_msg_size_in_Allgather/\
                                                                             self.Bandwidth_same_switch
        RS_Reduce_step1 = 0#unknown_array[0]*1000


        #Step 2
        RS_Num_of_phases_communication_happens_in_a_grp = math.floor(math.log(Min_number_of_nodes_participating_in_step2, 2))
        RS_Number_of_phases_communication_happens_outside_the_grp = int(math.log(self.Num_Ranks, 2))\
                                                                         - RS_Num_of_phases_communication_happens_in_a_grp
        RS_Number_of_phases_inside_the_switch = 3
        RS_Number_of_phases_inside_the_grp_across_switches = 2
        RS_Data_tranfer_within_switch_in_reduce_scatter =  self.scale_out_msg_size/2 +\
                                                                self.scale_out_msg_size/4 +self.scale_out_msg_size/8
        RS_Data_transfer_within_grp_across_switches = self.scale_out_msg_size/16 +self.scale_out_msg_size/32
        RS_Data_tranfer_outside_grp_in_reduce_scatter = self.scale_out_msg_size - \
                                                             RS_Data_tranfer_within_switch_in_reduce_scatter - \
                                                             RS_Data_transfer_within_grp_across_switches
        RS_reduce_scatter_bw = RS_Data_tranfer_within_switch_in_reduce_scatter/self.Bandwidth_same_switch\
                                    + RS_Data_transfer_within_grp_across_switches/self.Bandwidth_same_group_across_switch\
                                    + RS_Data_tranfer_outside_grp_in_reduce_scatter/self.Bandwidth_across_groups_per_node
        RS_reduce_scatter_lat = int(math.log(self.Num_Ranks, 2))*(unknown_DMA +self.RTS_CTS_overhead +
                                                                       self.Time_to_send_back_acknowledgement)
        RS_Reduce_step2 = 0#1000*sum(unknown_array[1:8])

        #Step 3
        RS_Participating_ranks_send_data_to_nonparticipating_ranks_in_same_grp = Total_msg_size_in_Allgather\
                                                                                      /self.Bandwidth_same_group_across_switch

        #Allgather
        #Step 1
        AG_Non_participating_ranks_send_data_to_participating_ranks_in_same_grp = Chunk_size_for_allgather/\
                                                                                  self.Bandwidth_same_group_across_switch
        AG_data_size = Chunk_size_for_allgather*2
        AG_Exchange = AG_data_size/self.Bandwidth_same_group_across_switch

        #Step 2
        AG_Num_of_phases_communication_happens_in_a_grp = 5
        AG_Number_of_phases_communication_happens_outside_the_grp = 2
        AG_Number_of_phases_inside_the_switch = 3
        AG_Number_of_phases_inside_the_grp_across_switches = 2
        AG_Data_transfer_outside_grp_in_allgather = AG_data_size+2*AG_data_size
        AG_Data_transfer_within_switch = Total_msg_size_in_Allgather-AG_Data_transfer_outside_grp_in_allgather
        AG_Data_transfer_inside_grp_different_switches = 0
        AG_Allgather_bw = AG_Data_transfer_within_switch/self.Bandwidth_same_switch+\
                          AG_Data_transfer_inside_grp_different_switches/self.Bandwidth_same_group_across_switch+\
                          AG_Data_transfer_outside_grp_in_allgather/self.Bandwidth_across_groups_per_node
        AG_Allgather_lat = int(math.log(self.Num_Ranks, 2)) * (unknown_DMA + self.RTS_CTS_overhead +
                                                                         self.Time_to_send_back_acknowledgement)
        #Step 3
        AG_Total_data_sent  =  Total_msg_size_in_Allgather
        AG_time = AG_Total_data_sent/self.Bandwidth_same_group_across_switch


        print([AG_Non_participating_ranks_send_data_to_participating_ranks_in_same_grp,AG_Exchange,AG_Allgather_bw,AG_Allgather_lat,AG_time])
        Total_reduce_scatter_time = RS_Time_to_send_data_to_participating_ranks_in_the_same_group+\
                                    RS_Reduce_step1+\
                                    RS_reduce_scatter_bw+\
                                    RS_reduce_scatter_lat+\
                                    RS_Reduce_step2+\
                                    RS_Participating_ranks_send_data_to_nonparticipating_ranks_in_same_grp
        Total_allgather_time = AG_time + AG_Allgather_lat+AG_Allgather_bw+AG_Exchange+\
                               AG_Non_participating_ranks_send_data_to_participating_ranks_in_same_grp
        Total = (Total_reduce_scatter_time+0.5*Total_reduce_scatter_time)+Total_allgather_time
        Total_15_percent_guardband = Total+0.15*Total
        Total_us = Total_15_percent_guardband/1000
        Total_ms = Total_us/1000

        #print(Total_reduce_scatter_time)
        return Total_ms


class comms_between_host_GPU():
    def __init__(self, config):
        self.Message_chunk_size = config["Message_chunk_size"]
        self.PCIe_BW_per_s_Read_or_Write = config["PCIe_BW_per_s_Read_or_Write"]
        self.no_of_cards = config["no_of_cards"]
        self.Msg_send_latency_sec = config["Msg_send_latency_sec"]

    def data_host_to_GPU(self):
        data_host_to_GPU_ns = ((self.Message_chunk_size/self.no_of_cards)/(self.PCIe_BW_per_s_Read_or_Write*0.8)
                               +self.Msg_send_latency_sec)*1000000000
        data_host_to_GPU_ms = data_host_to_GPU_ns*0.000001
        return data_host_to_GPU_ms

    def data_GPU_to_host(self):
        data_GPU_to_host_ns = ((self.Message_chunk_size/self.no_of_cards)/(self.PCIe_BW_per_s_Read_or_Write*0.8)
                               +self.Msg_send_latency_sec)*1000000000
        data_GPU_to_host_ms = data_GPU_to_host_ns*0.000001
        return data_GPU_to_host_ms
