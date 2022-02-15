import math
from collections import OrderedDict
from .constants import Constants


class Network(OrderedDict):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Network Constructor Check Fail!!"
        super(Network, self).__init__(knobs)
        self.derive_knobs_su()
        self.derive_knobs_so()

    def check_knobs(self, knobs):
        # add checks here
        return True

    def derive_knobs_su(self):
        """
        Derive scaleup knobs
        """
        # derived knobs
        self["L3_hit_remotetile_on_same_package"] = 552
        self["L3_hit_between_P0T0_P1T0"] = 1130

        if not (self["pipeline"]):
            self["latency_threshold_message_size_for_scale_out"] = Constants.LARGE_MSG_SZIE
            self["latency_threshold_message_size_for_scale_up"] = Constants.LARGE_MSG_SZIE
            self["latency_threshold_message_size_for_MDFI"] = Constants.LARGE_MSG_SZIE
        else:
            self["latency_threshold_message_size_for_scale_out"] = Constants.MB
            self["latency_threshold_message_size_for_scale_up"] = Constants.MB4000
            if self['so_enabled']:
                if self['so_hw_type'] == '3':
                    self["latency_threshold_message_size_for_MDFI"] = Constants.MB4000
                else:
                    self["latency_threshold_message_size_for_MDFI"] = Constants.MB4
            else:
                self["latency_threshold_message_size_for_MDFI"] = Constants.MB4

        if self['so_enabled']:
            if self['so_hw_type'] == 4:
                self["su_BW_per_link_PEAK"] = self["serdes_rate_gbps"] * self["serdes_lane"] / Constants.BYTE / 2
            else:
                self["su_BW_per_link_PEAK"] = self["serdes_rate_gbps"] * self["serdes_lane"] / Constants.BYTE
        else:
            self["su_BW_per_link_PEAK"] = self["serdes_rate_gbps"] * self["serdes_lane"] / Constants.BYTE

        self["other_latency_us"] = ((self["L3_read_cache_miss_for_data_from_remote_write"] +
                                     self["L3_read_cache_miss_on_sync_flag"] + self["sw_th_dispatch"]
                                     + self["L3_write_cache_hit_on_data"] +
                                     self["L3_write_cache_hit_on_sync_flag"] +
                                     self["L1_hit_per_cache_line"]) / (self["frequency_in_Ghz"] * 1000))

        self["max_achievable_read_memBW_no_congession"] = self["peak_read_memBW"] * self["read_memory_efficiency"]
        self["max_achievable_write_memBW_no_congession"] = self["peak_write_memBW"] * self["write_memory_efficiency"]

        self["max_achievable_read_memBW"] = self["max_achievable_read_memBW_no_congession"] * self[
            "memory_read_congestion_factor"]
        self["max_achievable_write_memBW"] = self["max_achievable_write_memBW_no_congession"] * self[
            "memory_write_congestion_factor"]
        self["mdfi_latency_us"] = 3 * self["mdfi_link_latency"] / (self["frequency_in_Ghz"] * 1000)
        self["total_mdfi_latency"] = min((self["mdfi_latency_us"] + self["other_latency_us"]),
                                         self["L3_hit_remotetile_on_same_package"] / (self["frequency_in_Ghz"] * 1000))
        self["fabric_efficiency"] = self["su_link_eff"] * self["su_packet_size"] / \
                                    (self["su_packet_size"] + self["su_msg_header"] + self["su_packet_resp"])
        if self["su_BW_per_link_ACHIEVABLE_overwrite"]:
            self["su_BW_per_link_ACHIEVABLE"] = self["su_BW_per_link_ACHIEVABLE_value"]
        else:
            self["su_BW_per_link_ACHIEVABLE"] = self["su_BW_per_link_PEAK"] * self["fabric_efficiency"]
        self["read_memBW_per_dss"] = self["g_memory_reads"] * self["frequency_in_Ghz"]
        self["achievable_read_L3_BW_with_congestion"] = self["L3_read_congestion_factor"] * self["read_memBW_per_dss"]
        self["write_memBW_per_dss"] = self["g_memory_writes"] * self["frequency_in_Ghz"]
        self["achievable_write_L3_BW_with_congestion"] = self["L3_write_congestion_factor"] * self[
            "write_memBW_per_dss"]
        self["xdim_3d_torus"] = 4
        self["ydim_3d_torus"] = 2
        self["zdim_3d_torus"] = 2

    def derive_knobs_so(self):
        """
        derive scaleout knobs
        """
        if self["data_parallel"]:
            self["so_data_parallel_with_model_split"] = 2
        self["so_total_lat_us"] = self["so_host_involvement"] + self["so_latency"]
        self["so_total_inter_host_bw_gbps"] = self["so_nics"] * self["so_nic_bw_unidir_gbps"] / 8 * self["so_nic_eff"]
        # Bandwidth multiplier in 1st tier
        self["so_t1_bw_mul"] = self["so_ports_t1"] / self["so_ports_switch"]
        # Bandwidth multiplier in 2nd tier
        self["so_t2_bw_mul"] = self["so_ports_t2"] / self["so_ports_switch"]
        self["so_tiles_per_host"] = self["num_tiles_per_pvc"] * self["num_PVC_per_host"]
        self["so_total_tiles"] = self["num_tiles_per_pvc"] * self["num_pvc"]
        self["so_tiles_in_comms"] = self["so_total_tiles"] / self["num_tiles_per_pvc"]
        self["so_host"] = round((self["num_pvc"] / self["num_PVC_per_host"]), 0)
        self["so_steps"] = math.log(self["so_host"], 2)
        self["so_per_dir_ring_bw"] = self["so_cafe_links"] / 2 * self["so_cafe_link_bw_gbps"] * 0.8

    def __str__(self):
        return self.__class__.__name__


class P2P(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(P2P, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Ring(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Ring, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Hypercube(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Hypercube, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class BidirRing(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(BidirRing, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Torus3d(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Torus3d, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Hypercube(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Hypercube, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Switch(Network):
    pass


class FatTree(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(FatTree, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True
    pass


class Flat(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Flat, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Pod(Network):
    def __init__(self, knobs):
        assert self.check_knobs(knobs)
        super(Pod, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True
