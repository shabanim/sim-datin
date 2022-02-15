from .multidispatch import multimethod
from .network import BidirRing, Network
from .collective import  AllReduce, AllGather, Gather, ReduceScatter, Scatter, Reduce, Broadcast, Collective
from .constants import Constants
from .stats import CommsStats

def su_latency_us(network, sockets):
    """
    get latency for scaleup due switch or gluless
    :param network: topology
    :param sockets: number of sockets
    :return: latency in micro seconds
    """
    su_switch_levels = max(1, sockets / network["su_grp_sockets"])
    if network["su_option"] == "SWITCH":
        return 3 * (network["cd_latency_ns"] * 2 +
                    (network["su_switch_lat_ns"] + network["su_link_lat_ns"] * 2) *
                    su_switch_levels) / 1000
    else:
        return 3 * (network["cd_latency_ns"] * 2 + network["su_link_lat_ns"]) / 1000


def su_msg_size_per_tile(network, message_size, tiles_per_socket, sockets):
    return min(message_size / (tiles_per_socket * network["su_cc_msg"]),
               network["latency_threshold_message_size_for_scale_up"] )


def local_metrics(network, reduce_gather_mdfi, reduce_gather_su, write_su):
    local_read_mdfi = reduce_gather_mdfi / \
                      min(network["dss_or_sms"] * network["achievable_read_L3_BW_with_congestion"],
                          network["max_achievable_read_memBW"])

    local_read_scale_up = reduce_gather_su / \
                          min(network["dss_or_sms"] * network["achievable_read_L3_BW_with_congestion"],
                              network["max_achievable_read_memBW"])

    local_write_scale_up = write_su / \
                           min(network["dss_or_sms"] * network["achievable_read_L3_BW_with_congestion"],
                               network["max_achievable_read_memBW"])
    return local_read_mdfi, local_read_scale_up, local_write_scale_up


def su_total_latency(network, su_lat_us):
    return min((network["other_latency_us"] + su_lat_us + network["total_mdfi_latency"]),
               ((network["L3_hit_between_P0T0_P1T0"] *1.5 )/( network["frequency_in_Ghz"] *1000) +
                (network["mdfi_link_latency"] / 2) / (network["frequency_in_Ghz"] * 1000)))

@multimethod(BidirRing, AllReduce)
def comms(bidirring, allreduce, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, tiles_per_socket, sockets)
    total_message_volume_bytes = 2 * (sockets - 1) * msg_size_per_scale_up_per_tile / sockets
    total_latency_for_scale_up = 2 * nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV)
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = 2 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (sockets * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = 2 * nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV)
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI = 2 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (tiles_per_socket * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW = 2 * min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                 * nsteps_MDFI / (tiles_per_socket * final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, AllGather)
def comms(bidirring, allgather, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, tiles_per_socket, sockets)
    total_message_volume_bytes =(sockets - 1) * msg_size_per_scale_up_per_tile / sockets
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (sockets * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =  nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (tiles_per_socket * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                 * nsteps_MDFI / (tiles_per_socket * final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, Gather)
def comms(bidirring, gather, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, tiles_per_socket, sockets)
    total_message_volume_bytes =(sockets - 1) * msg_size_per_scale_up_per_tile / sockets
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (sockets * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =  nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (tiles_per_socket * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                 * nsteps_MDFI / (tiles_per_socket * final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, ReduceScatter)
def comms(bidirring, reducescatter, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, tiles_per_socket, sockets)
    total_message_volume_bytes =(sockets - 1) * msg_size_per_scale_up_per_tile / sockets
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (sockets * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =  nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (tiles_per_socket * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                 * nsteps_MDFI / (tiles_per_socket * final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, Scatter)
def comms(bidirring, scatter, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, tiles_per_socket, sockets)
    total_message_volume_bytes =(sockets - 1) * msg_size_per_scale_up_per_tile / sockets
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (sockets * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =  nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (tiles_per_socket * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                 * nsteps_MDFI / (tiles_per_socket * final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, Reduce)
def comms(bidirring, reduce, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, 1, sockets)
    total_message_volume_bytes = msg_size_per_scale_up_per_tile
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (1 * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =   min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (1 * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                  / ( final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

@multimethod(BidirRing, Broadcast)
def comms(bidirring, broadcast, message_size, tiles_per_socket, sockets):
    links = bidirring["links"]
    nsteps_scaleup = sockets - 1
    su_lat_us = su_latency_us(bidirring, sockets)
    su_total_latency_us = su_total_latency(bidirring, su_lat_us)

    msg_size_per_scale_up_per_tile = su_msg_size_per_tile(bidirring, message_size, 1, sockets)
    total_message_volume_bytes = msg_size_per_scale_up_per_tile
    total_latency_for_scale_up = nsteps_scaleup * su_total_latency_us + bidirring["sw_lat_us"]

    if bidirring["use_full_message_size_in_HBM_latency_calculation"] == 1:
        local_reduce_plus_gather_scale_up = 3 * (sockets - 1) * min(msg_size_per_scale_up_per_tile,
                                                                    bidirring[
                                                                        "latency_threshold_message_size_for_scale_up"]) * \
                                            1000000 / (1 * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_scale_up = 0

    remote_write_scale_up = min(msg_size_per_scale_up_per_tile,
                                                     bidirring["latency_threshold_message_size_for_scale_up"]) * \
                            1000000 / (1 * Constants.GIGACONV)
    total_scale_up_BW = links * bidirring["su_BW_per_link_ACHIEVABLE"]

    Effective_remote_write_BW_over_MDFI = min(bidirring["max_achievable_write_memBW"],
                                              bidirring["mdfi_BW_per_tile_ACHIEVABLE"])

    no_of_concurrent_messages_over_mdfi = 0 if tiles_per_socket < 2 else tiles_per_socket / 2
    msg_size_per_MDFI_per_tile = 0 if not no_of_concurrent_messages_over_mdfi else message_size / no_of_concurrent_messages_over_mdfi
    nsteps_MDFI = tiles_per_socket - 1
    total_latency_for_MDFI = nsteps_MDFI * bidirring["total_mdfi_latency"]

    if bidirring["use_chunk_size_in_MDFI_latency_calculation"]:
        local_reduce_plus_gather_MDFI = 3 * nsteps_MDFI * min(msg_size_per_MDFI_per_tile,
                                                              bidirring[
                                                                  "latency_threshold_message_size_for_MDFI"]) * 1000000 / \
                                        (tiles_per_socket * Constants.GIGACONV) #Need to be fixed
    else:
        local_reduce_plus_gather_MDFI = 0
    local_write_scale_up = 0
    remote_write_MDFI =   min(msg_size_per_MDFI_per_tile,
                                              bidirring["latency_threshold_message_size_for_MDFI"]) * \
                        1000000 / (1 * Constants.GIGACONV)

    final_mdfi_latency = total_latency_for_MDFI
    final_scale_up_latency = total_latency_for_scale_up

    final_local_read_mdfi, final_local_read_scale_up, final_local_write_scale_up = local_metrics(
        bidirring,
        local_reduce_plus_gather_MDFI,
        local_reduce_plus_gather_scale_up,
        local_write_scale_up)

    try:
        final_remote_write_mdfi = remote_write_MDFI / \
                                  min(bidirring["dss_or_sms"] * bidirring["achievable_read_L3_BW_with_congestion"],
                                      bidirring["max_achievable_read_memBW"], Effective_remote_write_BW_over_MDFI)
    except ZeroDivisionError:
        final_remote_write_mdfi = 0

    final_remote_write_scale_up = remote_write_scale_up / min(
        (bidirring["dss_or_sms"] * bidirring["achievable_write_L3_BW_with_congestion"]),
        bidirring["max_achievable_write_memBW"],
        min(bidirring["dss_or_sms"], links) * bidirring["su_BW_per_link_ACHIEVABLE"])

    final_mdfi_time_us = final_mdfi_latency + final_local_read_mdfi + final_remote_write_mdfi

    if sockets != 1:
        final_scale_up_time_us = final_scale_up_latency + \
                                 final_local_read_scale_up + \
                                 final_local_write_scale_up + \
                                 final_remote_write_scale_up
    else:
        final_scale_up_time_us = 0

    final_total_time_us = final_mdfi_time_us + final_scale_up_time_us

    try:
        final_mdfi_achieved_BW =  min(msg_size_per_MDFI_per_tile, bidirring["latency_threshold_message_size_for_MDFI"]) \
                                  / ( final_mdfi_time_us / 1000000)
    except ZeroDivisionError:
        final_mdfi_achieved_BW = 0

    final_scale_up_achieved_BW = total_message_volume_bytes / (final_scale_up_time_us / 1000000)

    stats = CommsStats()
    stats.mdfi_bw = (bidirring["total_mdfi_BW"] * Constants.GIGACONV)
    stats.su_bw = (total_scale_up_BW * Constants.GIGACONV)
    stats.mdfi_latency = final_mdfi_latency
    stats.su_latency = final_scale_up_latency
    stats.local_read_mdfi = final_local_read_mdfi
    stats.su_local_read_ = final_local_read_scale_up
    stats.su_local_write = final_local_write_scale_up
    stats.remote_write_mdfi = final_remote_write_mdfi
    stats.su_remote_write = final_remote_write_scale_up
    stats.mdfi_time_us = final_mdfi_time_us
    stats.su_time_us = final_scale_up_time_us
    stats.total_time_us = final_total_time_us
    stats.mdfi_achieved_BW = final_mdfi_achieved_BW
    stats.su_achieved_BW = final_scale_up_achieved_BW

    return stats

