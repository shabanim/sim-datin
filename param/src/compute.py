import numpy as np
import csv


class Compute():
    def __init__(self):
        self.batch = 128
        self.len = 256
        self.head = 256
        self.d_model = 1024
        self.d_ff = 256*1024
        self.d_kv = 256
        self.layer = 6
        self.bpe = 2
        self.vocab = 36000
        self.freq_GHz  = 1.2
        self.eu = 1024
        self.mac_tpt = self.eu*128
        self.fp_tpt = self.eu*8
        self.mem_peak_GB_per_s = 4*128*3.2
        self.mem_eff = 0.675
        self.mem_B_per_clc = self.mem_peak_GB_per_s*self.mem_eff/self.freq_GHz
        self.xtile_uniD_peak = self.mem_peak_GB_per_s/4
        self.xtile_B_per_clk = self.mem_eff*self.xtile_uniD_peak/self.freq_GHz
        self.tiles_per_card = 2

        self.batch_divide = 8
        self.len_divide = 1
        self.head_divide = 4
        self.ff_divide = self.head_divide
        self.total_slicing = self.batch_divide*self.len_divide*self.head_divide
        self.cards_per_group = self.head_divide/self.tiles_per_card

        self.batch_per_tile = self.batch/self.batch_divide
        self.len_per_tile = self.len/self.len_divide
        self.head_per_tile = self.head/self.head_divide
        self.ffdim_per_tile = self.d_ff/self.ff_divide
        self.vocal_per_tile = self.vocab/self.ff_divide

    def qkv_projection(self):
        #mac in each head for each component at each position on a single layer on one tile
        mac_in_each_head = self.batch_per_tile*self.d_model*self.d_kv

        #input tensor (shared by QKV and heads) bytes for each component at each position on a single layer on one tile
        input_tensor_bytes = self.batch_per_tile*self.d_model*self.bpe

        #weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = self.d_model*self.d_kv*self.bpe

        #output tensor bytes  in each head for each component  at each position on a single layer on one tile
        output_tensor_bytes = self.d_kv*self.bpe*self.batch_per_tile

        #total mac for a single layer on one tile
        total_mac = mac_in_each_head*3*self.len_per_tile*self.head_per_tile

        #total input tensor MB for a single layer on one tile
        total_input_tensor_MB = input_tensor_bytes*self.len_per_tile/(1024*1024)

        #total weight MB for a single layer on one tile
        total_weight_MB = weight_bytes*3*self.head_per_tile/(1024*1024)

        #total_output_tensor_MB on a single layer on one tile
        total_output_tensor_MB = output_tensor_bytes*3*self.len_per_tile*self.head_per_tile/(1024*1024)

        matmul_instance = 1
        matmul_output_H = self.batch_per_tile*self.len_per_tile
        matmul_output_W = 3*self.d_kv*self.head_per_tile
        matmul_innerK = self.d_model
        mac_eff = 0.6
        mac_clk = total_mac/(self.mac_tpt*mac_eff)
        GT_incoming_HBM_clk = (total_input_tensor_MB+total_weight_MB)*1024*1024/self.mem_B_per_clc
        GT_outbound_HBM_clk = (total_output_tensor_MB)*1024*1024/self.mem_B_per_clc

        #remote vs local ratio for input
        input_remote_vs_local_ratio = (self.len_divide*self.head_divide)-1

        #remote vs local ratio for weight
        weight_remote_vs_local_ratio = (self.batch_divide*self.len_divide)-1

        #remote vs local ratio for output
        output_remote_vs_local_ratio = self.len_divide-1

        local_HBM_in_clk = ((total_input_tensor_MB/(input_remote_vs_local_ratio+1))+
                            (total_weight_MB/(weight_remote_vs_local_ratio+1)))*1024*1024/self.mem_B_per_clc
        remote_HBM_in_clk = ((total_input_tensor_MB*input_remote_vs_local_ratio/(input_remote_vs_local_ratio+1))+
                            (total_weight_MB*weight_remote_vs_local_ratio/(weight_remote_vs_local_ratio+1)))*1024*1024/\
                            self.xtile_B_per_clk
        local_HBM_out_clk = (total_output_tensor_MB/(output_remote_vs_local_ratio+1))*1024*1024/self.mem_B_per_clc

        remote_HBM_out_clk = (total_output_tensor_MB*output_remote_vs_local_ratio/(output_remote_vs_local_ratio+1))*\
                             1024*1024/self.xtile_B_per_clk
        final_clk = max(mac_clk,GT_incoming_HBM_clk+GT_outbound_HBM_clk,local_HBM_in_clk+local_HBM_out_clk,
                        remote_HBM_in_clk+remote_HBM_out_clk)
        return final_clk

    def self_Attn_InnerProd_and_Softmax(self):
        #mac in each head on a single layer on one tile
        mac_in_each_head = self.batch_per_tile*self.d_kv*self.len_per_tile*(self.len_per_tile+1)/2

        #scalar FP in each head on a single layer on one tile
        scalar_FP = self.batch_per_tile*self.len_per_tile*((self.len_per_tile+1)/2)*(4+4+4+1)

        #input tensor bytes in each head on a single layer on one tile
        input_tensor_bytes = 2*self.batch_per_tile*self.bpe*self.d_kv*self.len_per_tile

        #weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = 0

        #output tensor bytes  in each head on a single layer on one tile
        output_tensor = 4*self.len_per_tile*self.len_per_tile*self.batch_per_tile

        #total mac for a single layer on one tile
        total_mac = mac_in_each_head*self.head_per_tile

        #total scalar FP on a single layer on one tile
        total_scalar_FP = scalar_FP*self.head_per_tile

        #total input tensor MB for a single layer on one til
        total_input_tensor = input_tensor_bytes*self.head_per_tile/(1024*1024)

        #total weight MB for a single layer
        total_weight_MB = 0

        #total output tensor MB on a single layer on one tile
        total_output_tensor_MB = output_tensor*self.head_per_tile/(1024*1024)

        matmul_instance = self.batch_per_tile*self.head_per_tile
        matmul_output_H = self.len_per_tile
        matmul_output_W = self.len_per_tile
        matmul_innerK = self.d_kv
        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)
        fp_eff = 0.8
        fp_clk = total_scalar_FP/(self.fp_tpt *fp_eff)
        local_HBM_out_clk = total_output_tensor_MB*1024*1024/self.mem_B_per_clc
        final_clk= max(mac_clk+fp_clk,local_HBM_out_clk)

        return final_clk

    def self_Attn_scaled_weighting(self):
        #mac in each head on a single layer on one tile
        mac_in_each_head = self.batch_per_tile * self.d_kv * self.len_per_tile * (self.len_per_tile + 1) / 2

        # scalar FP in each head on a single layer on one tile
        scalar_FP = 0

        # input tensor bytes in each head on a single layer on one tile
        input_tensor_bytes = self.batch_per_tile * self.bpe * self.d_kv * self.len_per_tile

        # weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = 0

        # output tensor bytes  in each head on a single layer on one tile
        output_tensor = self.bpe * self.d_kv* self.len_per_tile * self.batch_per_tile

        # total mac for a single layer on one tile
        total_mac = mac_in_each_head * self.head_per_tile

        # total scalar FP on a single layer on one tile
        total_scalar_FP = scalar_FP * self.head_per_tile

        # total input tensor MB for a single layer on one til
        total_input_tensor = input_tensor_bytes * self.head_per_tile / (1024 * 1024)

        # total weight MB for a single layer
        total_weight_MB = 0

        # total output tensor MB on a single layer on one tile
        total_output_tensor_MB = output_tensor * self.head_per_tile / (1024 * 1024)

        matmul_instance = self.batch_per_tile * self.head_per_tile
        matmul_output_H = 255
        matmul_output_W = 255
        matmul_innerK = self.len_per_tile
        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)
        fp_eff = 0.8
        fp_clk = total_scalar_FP / (self.fp_tpt * fp_eff)
        local_HBM_out_clk = total_output_tensor_MB * 1024 * 1024 / self.mem_B_per_clc
        final_clk = max(mac_clk + fp_clk, local_HBM_out_clk)

        return final_clk

    def self_Attn_Concat_Merge_and_Layer_Norm(self):
        # total mac for a single layer on one tile
        total_mac = self.d_model*self.batch_per_tile* self.len_per_tile*self.d_kv*self.head_per_tile

        # total scalar FP on a single layer on one tile
        total_scalar_FP = self.batch_per_tile*self.len_per_tile*self.d_model*2

        # total input tensor MB for a single layer on one til
        total_input_tensor = self.bpe *self.d_kv* self.head_per_tile*self.len_per_tile*self.batch_per_tile / (1024 * 1024)

        # total weight MB for a single layer
        total_weight_MB = self.bpe *self.d_kv* self.head_per_tile*self.d_model / (1024 * 1024)

        # total output tensor MB on a single layer on one tile
        total_output_tensor_MB = self.bpe*self.batch_per_tile*self.len_per_tile*self.d_model / (1024 * 1024)

        matmul_instance = 1
        matmul_output_H = self.batch_per_tile * self.len_per_tile
        matmul_output_W = self.d_model
        matmul_innerK = self.d_kv*self.head_per_tile
        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)
        fp_eff = 0.8
        fp_clk = total_scalar_FP / (self.fp_tpt * fp_eff)
        L3_atomic_clk = total_output_tensor_MB * 1024 * 1024 * self.head_divide/(64*32)
        local_HBM_out_clk = total_output_tensor_MB * 1024 * 1024 / self.mem_B_per_clc
        weight_remote_vs_local_ratio = (self.batch_divide * self.len_divide) - 1
        remote_HBM_in_clk = ((total_weight_MB*weight_remote_vs_local_ratio/(weight_remote_vs_local_ratio+1))*1024*1024/self.xtile_B_per_clk)
        final_clk = max(mac_clk + fp_clk,L3_atomic_clk, local_HBM_out_clk,remote_HBM_in_clk)

        return final_clk

    def Fused_Self_Atnn(self):
        dummy_1 = self.self_Attn_InnerProd_and_Softmax()
        dummy_2 = self.self_Attn_scaled_weighting()
        dummy_3 = self.self_Attn_Concat_Merge_and_Layer_Norm()
        final_clk = dummy_1+dummy_2+dummy_3

        return final_clk

    def ff_1(self):
        #mac at each position on a single layer
        mac_in_each_head = self.d_model * self.batch_per_tile * self.ffdim_per_tile

        # total mac for a single layer on one tile
        total_mac = mac_in_each_head * self.len_per_tile

        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)

        # input tensor (shared by QKV and heads) bytes for each component at each position on a single layer on one tile
        input_tensor_bytes = self.batch_per_tile * self.d_model * self.bpe

        # total input tensor MB for a single layer on one tile
        total_input_tensor_MB = input_tensor_bytes * self.len_per_tile / (1024 * 1024)

        # weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = self.d_model * self.ffdim_per_tile * self.bpe

        # total weight MB for a single layer on one tile
        total_weight_MB = weight_bytes  / (1024 * 1024)

        # output tensor bytes  in each head for each component  at each position on a single layer on one tile
        output_tensor_bytes = self.ffdim_per_tile * self.bpe * self.batch_per_tile

        # total_output_tensor_MB on a single layer on one tile
        total_output_tensor_MB = output_tensor_bytes  * self.len_per_tile / (1024 * 1024)

        # remote vs local ratio for input
        input_remote_vs_local_ratio = self.ff_divide - 1

        weight_remote_vs_local_ratio = (self.batch_divide * self.len_divide) - 1

        # remote vs local ratio for output
        output_remote_vs_local_ratio = 0

        local_HBM_in_clk = ((total_input_tensor_MB / (input_remote_vs_local_ratio + 1)) +
                            (total_weight_MB / (weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / self.mem_B_per_clc
        remote_HBM_in_clk = ((total_input_tensor_MB * input_remote_vs_local_ratio / (input_remote_vs_local_ratio + 1)) +
                             (total_weight_MB * weight_remote_vs_local_ratio / (
                                         weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / \
                            self.xtile_B_per_clk
        local_HBM_out_clk = (total_output_tensor_MB / (
                    output_remote_vs_local_ratio + 1)) * 1024 * 1024 / self.mem_B_per_clc

        remote_HBM_out_clk = (total_output_tensor_MB * output_remote_vs_local_ratio / (
                    output_remote_vs_local_ratio + 1)) * \
                             1024 * 1024 / self.xtile_B_per_clk
        final_clk = max(mac_clk, local_HBM_in_clk + local_HBM_out_clk,
                        remote_HBM_in_clk + remote_HBM_out_clk)

        return final_clk

    def ff_2(self):
        # mac at each position on a single layer
        mac_in_each_head = self.d_model * self.batch_per_tile * self.ffdim_per_tile

        # total mac for a single layer on one tile
        total_mac = mac_in_each_head * self.len_per_tile

        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)

        # input tensor (shared by QKV and heads) bytes for each component at each position on a single layer on one tile
        input_tensor_bytes = self.batch_per_tile * self.ffdim_per_tile * self.bpe

        # total input tensor MB for a single layer on one tile
        total_input_tensor_MB = input_tensor_bytes * self.len_per_tile / (1024 * 1024)

        # weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = self.d_model * self.ffdim_per_tile * self.bpe

        # total weight MB for a single layer on one tile
        total_weight_MB = weight_bytes / (1024 * 1024)

        # output tensor bytes  in each head for each component  at each position on a single layer on one tile
        output_tensor_bytes = self.d_model * self.bpe * self.batch_per_tile

        # total_output_tensor_MB on a single layer on one tile
        total_output_tensor_MB = output_tensor_bytes * self.len_per_tile / (1024 * 1024)

        # remote vs local ratio for input
        input_remote_vs_local_ratio = 3

        weight_remote_vs_local_ratio = (self.batch_divide * self.len_divide) - 1

        # remote vs local ratio for output
        output_remote_vs_local_ratio = self.ff_divide - 1

        local_HBM_in_clk = ((total_input_tensor_MB / (input_remote_vs_local_ratio + 1)) +
                            (total_weight_MB / (weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / self.mem_B_per_clc
        remote_HBM_in_clk = ((total_input_tensor_MB * input_remote_vs_local_ratio / (input_remote_vs_local_ratio + 1)) +
                             (total_weight_MB * weight_remote_vs_local_ratio / (
                                     weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / \
                            self.xtile_B_per_clk
        local_HBM_out_clk = (total_output_tensor_MB / (
                output_remote_vs_local_ratio + 1)) * 1024 * 1024 / self.mem_B_per_clc
        remote_HBM_out_clk = (total_output_tensor_MB * output_remote_vs_local_ratio / (
                output_remote_vs_local_ratio + 1)) * \
                             1024 * 1024 / self.xtile_B_per_clk
        final_clk = max(mac_clk, local_HBM_in_clk + local_HBM_out_clk,
                        remote_HBM_in_clk + remote_HBM_out_clk)

        return final_clk

    def Projection(self):
        # mac at each position on a single layer
        mac_in_each_head = self.d_model * self.batch_per_tile * self.vocal_per_tile

        # total mac for a single layer on one tile
        total_mac = mac_in_each_head * self.len_per_tile

        mac_eff = 0.6
        mac_clk = total_mac / (self.mac_tpt * mac_eff)

        # input tensor (shared by QKV and heads) bytes for each component at each position on a single layer on one tile
        input_tensor_bytes = self.batch_per_tile * self.d_model * self.bpe

        # total input tensor MB for a single layer on one tile
        total_input_tensor_MB = 0#input_tensor_bytes * self.len_per_tile / (1024 * 1024)

        # weight bytes in each head for each component at each position on a single layer on one tile
        weight_bytes = self.d_model * self.vocal_per_tile * self.bpe

        # total weight MB for a single layer on one tile
        total_weight_MB = weight_bytes / (1024 * 1024)

        # output tensor bytes  in each head for each component  at each position on a single layer on one tile
        output_tensor_bytes = self.vocal_per_tile * self.bpe * self.batch_per_tile

        # total_output_tensor_MB on a single layer on one tile
        total_output_tensor_MB = output_tensor_bytes * self.len_per_tile / (1024 * 1024)

        # remote vs local ratio for input
        input_remote_vs_local_ratio = 3

        weight_remote_vs_local_ratio = (self.batch_divide * self.len_divide) - 1

        # remote vs local ratio for output
        output_remote_vs_local_ratio = 0

        local_HBM_in_clk = ((total_input_tensor_MB / (input_remote_vs_local_ratio + 1)) +
                            (total_weight_MB / (weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / self.mem_B_per_clc
        remote_HBM_in_clk = ((total_input_tensor_MB * input_remote_vs_local_ratio / (input_remote_vs_local_ratio + 1)) +
                             (total_weight_MB * weight_remote_vs_local_ratio / (
                                     weight_remote_vs_local_ratio + 1))) * 1024 * 1024 / \
                            self.xtile_B_per_clk
        local_HBM_out_clk = (total_output_tensor_MB / (
                output_remote_vs_local_ratio + 1)) * 1024 * 1024 / self.mem_B_per_clc
        remote_HBM_out_clk = (total_output_tensor_MB * output_remote_vs_local_ratio / (
                output_remote_vs_local_ratio + 1)) * \
                             1024 * 1024 / self.xtile_B_per_clk
        final_clk = max(mac_clk, local_HBM_in_clk + local_HBM_out_clk,
                        remote_HBM_in_clk + remote_HBM_out_clk)

        return final_clk














