import csv
import pandas
import yaml


def read_arch_csv(fname):
    with open(fname) as fin1:
        stat = [row for row in csv.DictReader(fin1)]
        return stat


def model_split_file_read(fname):
    layer_stat = read_arch_csv(fname)
    fwd_list = []
    bwd_list = []
    for i in range(len(layer_stat)):
        if (layer_stat[i]['pass'] == 'fwd'):
            # print('n')
            fwd_list.append({'Name': layer_stat[i]['Name'],
                             'type': layer_stat[i]['type'],
                             'comms_type': layer_stat[i]['comms_type'],
                             'pass':layer_stat[i]['pass_2'],
                             'pick':layer_stat[i]['pick']})
        else:
            # print(i)
            bwd_list.append({'Name': layer_stat[i]['Name'],
                             'type': layer_stat[i]['type'],
                             'comms_type': layer_stat[i]['comms_type'],
                             'pass':layer_stat[i]['pass_2'],
                             'pick':layer_stat[i]['pick']})
    # print(fwd_list)
    # print(bwd_list)
    return fwd_list, bwd_list


def read_config(fname):
    if fname is None:
        return None
    with open(fname) as fin:
        reader = csv.reader(fin)
        return {row[0]: row[1] for row in reader if len(row) > 0}


def _get_range(loop_range):
    lst = loop_range.split(',')
    if len(lst) != 3:
        raise ("invalid range to be given in format start,stop,step eg 0,10,1")
    if lst[2] == 'pow2':
        return float(lst[0]), float(lst[1]), 'pow2'
    return float(lst[0]), float(lst[1]), float(lst[2])


def frange(loop_range, precision=2):
    (start, stop, step) = _get_range(loop_range)
    x = start
    while x <= stop:
        yield x
        if step == 'pow2':
            x *= 2
        else:
            x += step
        x = round(x, precision)


def get_config_df(knobs):
    config_df = [("No of cards", knobs["num_PVC_per_host"]),
                 ("No of tiles per card", knobs["num_tiles_per_pvc"]),
                 ("Batch size", knobs["batch_size"]),
                 ("Network Topology", knobs["scale_up_collectiveAlgo"]["nw_topology"]),
                 ("Frequency", knobs["frequency_in_Ghz"]),
                 ("Scale up option", knobs["su_option"]),
                 ("Serdes rate (Gbps)", knobs["serdes_rate_gbps"])
                 ]
    if knobs["use_buffer"]:
        config_df.append(("Buffers", "Enabled"))
        config_df.append(("Buffer size", knobs["buffer_size"]))
    else:
        config_df.append(("Buffers", "Disabled"))
    if knobs["so_enabled"]:
        config_df.append(("No of PVC", knobs["num_pvc"]))
        config_df.append(("No of tiles per PVC", knobs["num_tiles_per_pvc"]))
        config_df.append(("No of PVC per host", knobs["num_PVC_per_host"]))
        config_df.append(("Bw per NIC unidirection (Gbps)", knobs["so_nic_bw_unidir_gbps"]))
    return pandas.DataFrame(config_df, columns=["HW Parameter", "Value"])


def _combine_dataframes(dataframes):
    """
    Combine data frames based on an index
    Assume dataframe index represents the key.
    :param dataframes: a map from data frame name to a data frame
    :return: merged dataframe with multi-index columns
    """
    multi_index = []
    names_dfs = [(name, df.add_suffix('_' + str(name))) for name, df in dataframes.items()]
    orig_dfs = [df for df in dataframes.values()]
    dfs = [i[1] for i in names_dfs]
    names = [i[0] for i in names_dfs]
    for c in orig_dfs[0].columns:
        for name in names:
            multi_index.append((c, name))

    merged = pandas.DataFrame(columns=pandas.MultiIndex.from_tuples(multi_index))
    inner_merged = dfs[0]

    for name_df in names_dfs[1:]:
        inner_merged = inner_merged.merge(
            name_df[1], left_index=True, right_index=True, how='outer'
        )

    for c in orig_dfs[0].columns:
        for name in names:
            merged[(c, name)] = inner_merged[c + '_' + str(name)]

    merged.index.name = orig_dfs[0].index.name
    return merged


def combine_dataframes(dataframes, index=None):
    """
    combine data frames based on an index.
    The set of columns that should be treated as index is specified in "index'
    :param dataframes: a map from data frame name to a data frame
    :param index: the index
    :return: the combined data frame
    """
    if index is not None:
        for name in dataframes:
            dataframes[name] = dataframes[name].set_index(index)

    result = _combine_dataframes(dataframes)
    result.reset_index(inplace=True)
    return result


def update_archbench_config(archbench_config, param1, value1, param2=None, value2=None):
    rfile = open(archbench_config, 'r')
    config = yaml.safe_load(rfile)
    update = False

    if param1 == "frequency_in_Ghz":
        update = True
        config['Device']['deviceFreq'] = [float(value1) * 1000]
    if param2 == "frequency_in_Ghz":
        update = True
        config['Device']['deviceFreq'] = [float(value2) * 1000]

    if param1 == "batch_size":
        update = True
        config['Device']['layerBatches'] = float(value1)
    if param2 == "batch_size":
        update = True
        config['Device']['layerBatches'] = float(value2)

    if update:
        wfile = open(archbench_config, 'w')
        yaml.dump(config, wfile)


def merge_overlapping_intervals(intervals):
    # Sorting based on the increasing order
    # of the start intervals
    intervals.sort(key=lambda x: x[0])

    # array to hold the merged intervals
    m = []
    s = -10000
    max = -100000
    for i in range(len(intervals)):
        a = intervals[i]
        if a[0] > max:
            if i != 0:
                m.append([s, max])
            max = a[1]
            s = a[0]
        else:
            if a[1] >= max:
                max = a[1]

    # 'max' value gives the last point of
    # that particular interval
    # 's' gives the starting point of that interval
    # 'm' array contains the list of all merged intervals

    if max != -100000 and [s, max] not in m:
        m.append([s, max])
    return m


def interval2duration(intervals):
    duration = []
    for interval in intervals:
        duration.append(interval[1] - interval[0])
    return duration


def get_overlap_duration(interval1: pandas.Interval, interval2: pandas.Interval) -> float:
    duration1 = interval1.right - interval1.left
    duration2 = interval2.right - interval2.left
    start = interval1.left if interval1.left < interval2.left else interval2.left
    end = interval1.right if interval1.right > interval2.right else interval2.right
    overlapped_duration = end - start

    return duration1 + duration2 - overlapped_duration
