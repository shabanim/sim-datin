import pandas
import json
from reports.report import Report, Section, Table, ContentGroup, BarChart, DataSeries, IntervalChart, \
    IntervalDataSeries
from reports import render_report

from reports import BarChart, PieChart, ScatterChart, IntervalChart, ScatterDataSeries


class OverlapSummaryReport:
    """
    Summary of overlap algorithm runs
    """

    def __init__(self, name=None, info_df=None, sim_summary=None, run_analysis=None):
        self.name = name
        self.info_df = info_df
        self.sim_summary = sim_summary
        self.run_analysis = run_analysis


def format_summary_report(condfig_df, summary, include_timeline=False) -> Report:
    sections = list()
    sections.append(Section("HW config", Table(condfig_df)))
    results_df = []
    for tool_name, result in summary.items():
        result.info_df.rename(columns={"Value": "{}".format(tool_name)})
        results_df.append(result.info_df)
        if include_timeline:
            sections.append(Section('{} Task analysis'.format(tool_name),
                                    IntervalChart('Task analysis',
                                                  *[IntervalDataSeries(row['TRANSITION'], [row["START (ms)"]],
                                                                       [row['RESOURCE']],
                                                                       [row["DURATION (ms)"]]) for i, row in
                                                    result.run_analysis.iterrows()],
                                                  y_axis_ticks=list(
                                                      result.run_analysis[
                                                          'RESOURCE'].unique()) if not result.run_analysis.empty else None,
                                                  sizehint='large')))
        result.run_analysis.to_csv("./modelzoo/{}_TaskAnalysis.csv".format(tool_name))

    if len(summary) == 1:
        sections.append(Section("Run Summary", Table(summary["SpeedSim"].info_df)))
    if len(summary) == 2:
        run_summary = results_df[0].merge(results_df[1], on=["Metric"])
        run_summary = run_summary.rename(columns={"Value_x": "Speedsim", "Value_y": "Fabsim"})
        sections.append(Section("Run Summary", Table(run_summary)))

    return Report("Overlap Analysis", *sections)


def format_loop_summary(summary_df, sweep_param1, sweep_param2=None, scaling_graph=None, thoughput_graph=None):
    sections = [Section("Loop Summary", Table(summary_df))]
    if sweep_param2 is not None:
        if scaling_graph is not None:
            scaling_series = []
            for key in scaling_graph.keys():
                (x, y) = scaling_graph[key]
                scaling_series.append(ScatterDataSeries("{} {}".format(sweep_param1, key), x=x, y=y, step=False))
            scaling_chart = ScatterChart("Scaling efficiency", *scaling_series, xtitle=sweep_param2)
            sections.append(Section("", scaling_chart))
        if thoughput_graph is not None:
            throughput_series = []
            for key in thoughput_graph.keys():
                (x, y) = thoughput_graph[key]
                throughput_series.append(ScatterDataSeries("{} {}".format(sweep_param1, key), x=x, y=y, step=False))
            throughput_chart = ScatterChart("Throughput full overlap", *throughput_series, xtitle=sweep_param2)
            sections.append(Section("", throughput_chart))
    else:
        if scaling_graph is not None:
            x = []
            y = []
            for key in scaling_graph.keys():
                x.append(key)
                y.append(scaling_graph[key])
            scaling_chart = ScatterChart("Scaling efficiency",
                                         ScatterDataSeries("", x=x, y=y, step=False), xtitle=sweep_param1)
            sections.append(Section("", scaling_chart))
        if thoughput_graph is not None:
            x = []
            y = []
            for key in thoughput_graph.keys():
                x.append(key)
                y.append(thoughput_graph[key])
            throughput_chart = ScatterChart("Throughput full overlap",
                                            ScatterDataSeries("", x=x, y=y, step=False), xtitle=sweep_param1)
            sections.append(Section("", throughput_chart))
    return Report("Loop summary", *sections)


def add_comms_stats(layer_stats_path, out_path, wl_json_file):
    """
    Adds comms stats/idle cycles to layer_stats and saves in outpath
    """
    wl_json_fd = open(wl_json_file, 'r')
    wl_json = json.load(wl_json_fd)
    comms_su = {}
    comms_so = {}
    comms_msg = {}

    msg_sub_task = ["wt_grad_msg_size", "fwd_pass_msg_size", "inp_grad_msg_size"]
    scaleup_sub_tasks = ['comms_time_fwd_cycles', 'comms_time_inp_grad_cycles', 'comms_time_wtgrad_cycles']
    scaleout_sub_tasks = ['comms_scaleout_time_fwd_cycles_pod','comms_scaleout_time_fwd_cycles_nic', 'comms_scaleout_time_inp_cycles_pod','comms_scaleout_time_inp_cycles_nic',
                          'comms_scaleout_time_wt_cycles_pod','comms_scaleout_time_wt_cycles_nic']

    for layer in wl_json['nodes']:
        layer_name = layer['data']['Layer']['Layer Name']
        l_comms_su = 0
        l_comms_so = 0
        l_msg = 0
        for sub_task in scaleup_sub_tasks:
            l_comms_su += float(layer['data']['Layer'][sub_task])
        for sub_task in scaleout_sub_tasks:
            l_comms_so += float(layer['data']['Layer'][sub_task])
        for sub_task in msg_sub_task:
            l_msg += float(layer['data']['Layer'][sub_task])
        comms_su[layer_name] = l_comms_su
        comms_so[layer_name] = l_comms_so
        comms_msg[layer_name] = l_msg


    layer_stats_df = pandas.read_csv(layer_stats_path, index_col=[0])
    layer_stats_df["COMM_SU"] = layer_stats_df["NAME"].map(comms_su)
    layer_stats_df["COMM_SO"] = layer_stats_df["NAME"].map(comms_so)
    layer_stats_df["COMM_MSG"] = layer_stats_df["NAME"].map(comms_msg)
    layer_stats_df.to_csv(out_path)
