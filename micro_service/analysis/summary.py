import os
import ntpath
from time import time
import subprocess
import pandas
import getpass


import sys

if os.name == "nt":
    path = '.\\param\\'
else:
    path = './param/'

if path not in sys.path:
    sys.path.append(path)

from src import comms_wrapper
from .overlap_analysis import speedsim_analysis, fabsim_analysis
from .parser import parse_graph
from .parser_train import parse_graph as parse_graph_train
from report_objects import add_comms_stats
from src.knobs import Knobs
from .splunk_upload import upload


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def _get_archbench_args(project_dir, outdump, study, filter, filtersku):
    results_dir = os.path.join(project_dir, outdump, study)
    from os import listdir
    from os.path import isfile, join

    res_dir = ""
    workload_json = ""
    for root, subdirs, files in os.walk(results_dir):
        for file in files:
            if '_graph.json' in file and filter in root and filtersku in root and '.bak' not in root:
                res_dir = root
                workload_json = file
        for files_ in files:
            if '_layerstats.csv' in files_ and 'SUMMARY' in root:
                compstat_root = root
                compstat = files_

    onlyfiles = [f for f in listdir(res_dir) if isfile(join(res_dir, f))]
    # compstat = [files for files in onlyfiles if "FSPS" in files][0]
    layerstat = [files for files in onlyfiles if "layer_stat" in files][0]

    return (
        os.path.join(res_dir, workload_json), os.path.join(compstat_root, compstat), os.path.join(res_dir, layerstat),
        os.path.join(os.path.join(res_dir, os.pardir), 'LayerStats.csv'))


def get_ab_config_name(outdump, study, filterskus, filter):
    results_dir = os.path.join(MASTER_DIR, outdump, study)
    from os import listdir
    from os.path import isfile, join

    res_dir = ""
    workload_json = ""
    for root, subdirs, files in os.walk(results_dir):
        for file in files:
            if '_graph.json' in file and filter in root and filterskus in root and '.bak' not in root:
                res_dir = root

    config_dir = os.path.join(os.path.join(res_dir, os.pardir), '0_config_files')
    onlyfiles = [f for f in listdir(config_dir) if isfile(join(config_dir, f)) and '-with-overrides' in f]
    return os.path.join(config_dir, onlyfiles[0])


def _get_param_args(knobs, workload_graph_path):
    workload_graph = ntpath.basename(workload_graph_path)
    outFilePath = ""
    try:
        outFilePath = knobs["outFilePath"]
    except:
        pass
    if outFilePath is None or len(outFilePath) <= 0:
        outFilePath = os.path.normpath("./modelzoo/")
    # (workloadconfig, workloadcompute, workload_json)
    return (os.path.join(outFilePath, "comms.csv"),
            os.path.join(outFilePath, "compute.csv"),
            os.path.join(outFilePath, workload_graph.strip('.json') + '_out.json'))


MASTER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def invoke_ab_release_automation(args):
    cmd = ['python', os.path.join(MASTER_DIR, 'ab-release-automation', 'generate_targets.py')]
    cmd += args
    subprocess.check_call(cmd)


def invoke_archbench(args):
    command = "python \"{}\"".format(os.path.join(MASTER_DIR, 'archbench', 'archbench.py'))
    for key, val in args.items():
        if key == "trg_corr" or key == "trg_optimizer" or key == "trg_loss_function" or key == "trg_per_layer_flush" or \
                key == "trg_endofpass_flush" or key == "trg_imm_wt_update" or key == "trg_bwd_pipe_layer_inp-save" or \
                key == "trg_resnet_specific":
            key = key.replace("_", "-")
        if val is not None:
            if (key == "dump_html" and val == True) or \
                    (key == "training" and val == True) or \
                    (key == "no_backup" and val == True) or \
                    (key == "rf" and val == True) or \
                    (key == "v" and val == True) or \
                    (key == "os" and val == True) or \
                    (key == "no_reports" and val == True) or \
                    (key == "trg-corr" and val == True) or \
                    (key == "trg-resnet-specific" and val == True):
                command += " --{}".format(key)

            elif val is not False and key != "logging":
                command += " --{} \"{}\"".format(key, val)

    print(command)

    ret_val = os.system(command)
    print("Archbench return value {}".format(ret_val))
    return ret_val


def invoke_readGraph_parser(knobs, worload_graph, prototxt_stats, layer_stats, istraining=False):
    if istraining:
        parse_graph_train(knobs, worload_graph, prototxt_stats, layer_stats)
    else:
        parse_graph(knobs, worload_graph, prototxt_stats, layer_stats)


def invoke_param(knobs, workloadconfig, workloadcompute, outputfile, workload_graph):
    if knobs["so_enabled"]:
        comms_wrapper(knobs=knobs, comms_csv=workloadconfig,
                      compute_csv=workloadcompute, output_file_path=outputfile,
                      workload_graph=workload_graph)
    else:
        comms_wrapper(knobs=knobs, comms_csv=workloadconfig,
                      compute_csv=workloadcompute, output_file_path=outputfile,
                      workload_graph=workload_graph)


def invoke_speedsim(workload_json, knobs, include_timeline=False, network_name=None):
    if knobs['Zero-inf']:
        from .overlap_zero_inf import speedsim_analysis_zero_inf
        return speedsim_analysis_zero_inf(workload_json, knobs, include_timeline, network_name)
    else:
        return speedsim_analysis(workload_json, knobs, include_timeline, True, network_name)


def invoke_fabsim(fabsim_trace, scaleup_run_log, scaleout_run_log, knobs, network_name):
    return fabsim_analysis(fabsim_trace, scaleup_run_log, scaleout_run_log, knobs, network_name)


def archbench(args_dict):
    invoke_archbench(args_dict)


def param(args_dict, workload_graph_path, archbench_config, knobs, outputfile, include_timeline=False):
    (jsonfile, compstat, layerstat) = _get_archbench_args(workload_graph_path, archbench_config)
    (workloadconfig, workloadcompute, workload_json) = _get_param_args(knobs, workload_graph_path)
    invoke_readGraph_parser(knobs, jsonfile, compstat, layerstat, args_dict["training"])
    invoke_param(knobs, workloadconfig, workloadcompute, outputfile, workload_json)
    workload_graph = ntpath.basename(workload_graph_path)
    network_name = ntpath.basename(workload_graph)
    ss_report = invoke_speedsim(workload_json, knobs, include_timeline, network_name)
    return ss_report


def ubench(message_size, algo, knobs, outputfile):
    workloadconfig = "./modelzoo/ubench/comms.csv"
    workloadcompute = "./modelzoo/ubench/compute.csv"
    workload_json = "./modelzoo/ubench/ubench.prototxt_graph_out.json"
    import json

    # update workload json
    with open(workload_json, "r") as jsonFile:
        wl_json = json.load(jsonFile)
    wl_json['nodes'][0]['data']['Layer']['wt_grad_msg_size'] = float(message_size)
    with open(workload_json, "w") as jsonFile:
        json.dump(wl_json, jsonFile)

    # comms.csv
    no_socket_list = knobs["num_PVC_per_host"]
    tile_per_socket_list = knobs["num_tiles_per_pvc"]
    # algo = "allreduce"
    with open(workloadconfig, "w") as comms_file:
        # dont add space to below line
        lines = ["Msg_size,algo,No_of_GPU,No_of_tile_per_socket,MSG_PASS_Type,layer_ID\n",
                 "{},{},{},{},WT_GRAD,1".format(message_size, algo,
                                                no_socket_list,
                                                tile_per_socket_list)]
        comms_file.writelines(lines)

    invoke_param(knobs, workloadconfig, workloadcompute, outputfile, workload_json)

    # get results from workload
    with open(workload_json, "r") as jsonFile:
        wl_json = json.load(jsonFile)
    if wl_json:
        scaleup_time = float(wl_json['nodes'][0]['data']['Layer']['comms_time_wtgrad_cycles']) / \
                       (knobs['frequency_in_Ghz'] * 1000000)
        scaleout_time = float(wl_json['nodes'][0]['data']['Layer']['comms_scaleout_time_wt_cycles']) / \
                        (knobs['frequency_in_Ghz'] * 1000000)
        return scaleup_time, scaleout_time


def invoke_cam(outdump, study, compderate=0.95, compderatethreshold=0.3):
    log = os.path.join(outdump, study, '{}.log'.format(study))
    outdir = os.path.join(os.path.join(outdump, study, "SUMMARY"))

    cmd = ['python', os.path.join(MASTER_DIR, 'ab-release-automation', 'summarize_layer_stats.py'),
           '-i', log,
           '-o', outdir,
           '--study', study,
           '--compderate', compderate,
           '--comms', 'True',
           '--compderatethreshold', compderatethreshold]
    subprocess.check_call(cmd)


def list2dict(lst):
    res_dct = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}
    return res_dct


def get_upload_data(aggr_summary, ss_report, network_name):
    ss_report_dict = {}
    for key, value in zip(list(ss_report.info_df.transpose().iloc[0]), list(ss_report.info_df.transpose().iloc[1])):
        ss_report_dict[key] = value

    data_df = pandas.read_csv(aggr_summary)
    print(ss_report_dict)
    data = {"user": getpass.getuser(),
            "ab-rev": data_df.iloc[0]["AB-Rev"],
            "ra-rev": data_df.iloc[0]["RA-Rev"],
            "data-rev": data_df.iloc[0]["Data-Rev"],
            "param-rev": "12e7896",
            "param_release_automation": "61e7896",
            "wl_Name": data_df.iloc[0]["Workload"],
            "ab_Name": data_df.iloc[0]["Name"],
            "param_config": data_df.iloc[0]["Config"],
            "tflops_AB": data_df.iloc[0]["TFLOPS"],
            "MACEff_AB": data_df.iloc[0]["MACEff"],
            "Compute_Time_AB": data_df.iloc[0]["TIME(MSEC)"],
            "Compute_Comms_overlap": True,
            "Scaleup_Comms_Time": ss_report_dict["Scale Up no overlap time (ms)"],
            "Scaleout_Comms_Time_NIC": "NA",
            "Scaleout_Comms_Time_POD": "NA",
            "Total_Comms_Time_scaleout": "NA",
            "Total_Comms_Time": 456465,
            "Total_time": 4654654,
            "score": data_df.iloc[0]["Score"],
            "Scaling_Efficiency": ss_report_dict["Scaling efficiency (%)"]
            }

    print(data)
    upload(data)


def summary(args_list, knobs_file, outputfile, fabsim_trace=None,
            fabsim_scaleup_run_log=None, fabsim_scaleout_run_log=None, include_timeline=False, upload=False):
    """

    :param workload_graph:
    :param archbench_config:
    :param configfile:
    :param outputfile:
    :param scaleout_config:
    :param scaleout:
    :return:
    """

    invoke_ab_release_automation(args_list)
    outdump = args_list[args_list.index('-o') + 1]
    study = args_list[args_list.index('-s') + 1]
    filterskus = args_list[args_list.index('--filtersku') + 1]
    filter = args_list[args_list.index('--filter') + 1]

    ab_config = get_ab_config_name(outdump, study, filterskus, filter)

    knobs = Knobs(knobs_file, ab_config)

    compderate = '0.95'
    if '--compderate' in args_list:
        compderate = args_list[args_list.index('--compderate') + 1]
    compderatethreshold = '0.3'
    if '--compderatethreshold' in args_list:
        compderatethreshold = args_list[args_list.index('--compderatethreshold') + 1]

    (jsonfile, compstat, layerstat, cam_stats) = _get_archbench_args(MASTER_DIR, outdump, study, filter, filterskus)

    start_secs = time()
    (workloadconfig, workloadcompute, workload_json) = _get_param_args(knobs, jsonfile)

    invoke_readGraph_parser(knobs, jsonfile, compstat, layerstat, True)
    print("Graph parser: Completed jobb in {}".format(time() - start_secs))
    start_secs = time()
    invoke_param(knobs, workloadconfig, workloadcompute, outputfile, workload_json)
    print("Param: Completed jobb in {}".format(time() - start_secs))
    start_secs = time()
    network_name = ntpath.basename(jsonfile)
    ss_report = invoke_speedsim(workload_json, knobs, include_timeline, network_name)
    # print("cam_stats", cam_stats)
    aggr_summary = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(cam_stats)))), "SUMMARY", "AGGR-summary.csv")
    add_comms_stats(cam_stats, cam_stats, workload_json)

    # invoke_cam(outdump, study, compderate, compderatethreshold)
    print("SpeedSim: Completed jobb in {}".format(time() - start_secs))

    if upload:
        get_upload_data(aggr_summary, ss_report, network_name)

    if fabsim_trace and (fabsim_scaleup_run_log or fabsim_scaleout_run_log):
        start_secs = time()
        fabsim_report = invoke_fabsim(fabsim_trace, fabsim_scaleup_run_log, fabsim_scaleout_run_log, knobs,
                                      network_name)
        print("fabsim: Completed jobb in {}".format(time() - start_secs))
        return {"SpeedSim": ss_report,
                "Fabsim": fabsim_report
                }

    return {"SpeedSim": ss_report}
