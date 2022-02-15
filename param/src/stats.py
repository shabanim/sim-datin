class CommsStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.mdfi_bw = 0
        self.su_bw = 0
        self.mdfi_latency = 0
        self.su_latency = 0
        self.local_read_mdfi = 0
        self.su_local_read = 0
        self.su_local_write = 0
        self.remote_write_mdfi = 0
        self.su_remote_write = 0
        self.mdfi_time_us = 0
        self.su_time_us = 0
        self.total_time_us = 0
        self.mdfi_achieved_BW = 0
        self.su_achieved_BW = 0

    @property
    def mdfi_Local_R_W_sum_percentage(self):
        if self.mdfi_time_us:
            return self.local_read_mdfi * 100 / self.mdfi_time_us
        return 0

    @property
    def mdfi_latency_percentage(self):
        if self.mdfi_time_us:
            return self.mdfi_latency * 100 / self.mdfi_time_us
        return 0

    @property
    def mdfi_write_percentage(self):
        if self.mdfi_time_us:
            return self.remote_write_mdfi * 100 / self.mdfi_time_us
        return 0

    @property
    def peak_BW_mdfi_percentage(self):
        if self.mdfi_time_us:
            return self.mdfi_achieved_BW * 100 / self.mdfi_bw
        return 0

    @property
    def su_latency_percentage(self):
        if self.su_time_us:
            return self.su_latency * 100 / self.su_time_us
        return 0

    @property
    def su_local_R_W_sum_percentage(self):
        if self.su_time_us:
            return (self.su_local_read + self.su_local_write) * 100 / self.su_time_us
        return 0

    @property
    def su_write_percentage(self):
        if self.su_time_us:
            return self.su_remote_write * 100 / self.su_time_us
        return 0

    @property
    def su_peak_bw_percentage(self):
        if self.su_bw:
            return self.su_achieved_BW * 100 / self.su_bw
        return 0



