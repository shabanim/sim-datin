import os
import sys
import tempfile
from collections import namedtuple

from numpy import arange
from pandas import DataFrame, ExcelWriter, concat, read_csv

from asap.strings import HW_ANALYSIS, TASK_ANALYSIS, ResourceDesc
from reports import render_report
from reports.report import (BarChart, ContentGroup, DataSeries, IntervalChart,
                            IntervalDataSeries, Report, Section, Table)

from .setup import (DATA, EMPTY, FINISH_COLUMN, SMALL, START_COLUMN, TABLE,
                    TIME_COLUMN, TITLE, TYPE)

SPACE = '                               '
HW_EVENT_RESOURCE = 'RESOURCE'
HW_EVENT_START = START_COLUMN
HW_EVENT_FINISH = FINISH_COLUMN
HW_EVENT_DURATION = 'DURATION'
NAN = float('NaN')

# Each simulation saves hw_events on the hw_data singleton with information about the ips, buses and memories
HW_EVENT = namedtuple('HW_EVENT', (HW_EVENT_RESOURCE, HW_EVENT_START, HW_EVENT_FINISH))


class AnalysisData:
    """
    A singleton that stores all of the hw analysis data during the simulation
    """
    class _AnalysisData:
        def __init__(self):
            self.ip_data = list()
            self.memory_data = list()
            self.bus_data = list()
            self.task_data = DataFrame()
            # for internal use of the scheduler
            self.task_to_memory = dict()  # Dictionary to save task to memory target during task scheduling
            self.task_to_path = dict()    # Dictionary to save task to route path to memory (all buses on the way)
            # during task scheduling
            self.simulation_time = 0  # The duration of the simulation
            self.start_triggers = list()  # List of start triggers that was simulated
            self.task_table = DataFrame()  # Runtime table of tasks after simulation
            self.extended_task_table = DataFrame()

    instance = None

    def __init__(self):
        if not AnalysisData.instance:
            AnalysisData.instance = AnalysisData._AnalysisData()

    @staticmethod
    def add_net(transition_name):
        AnalysisData.instance.start_triggers.append(transition_name)

    @staticmethod
    def add_ip_event(ip_event):
        AnalysisData.instance.ip_data.append(ip_event)

    @staticmethod
    def add_memory_event(memory_event):
        AnalysisData.instance.memory_data.append(memory_event)

    @staticmethod
    def add_bus_event(bus_event):
        AnalysisData.instance.bus_data.append(bus_event)

    @staticmethod
    def reset():
        if AnalysisData.instance is None:
            return
        AnalysisData.instance.task_to_memory.clear()
        AnalysisData.instance.task_to_path.clear()
        AnalysisData.instance.ip_data.clear()
        AnalysisData.instance.memory_data.clear()
        AnalysisData.instance.bus_data.clear()
        AnalysisData.instance.task_table = DataFrame()
        AnalysisData.instance.simulation_time = 0
        AnalysisData.instance.start_triggers = list()


AnalysisData()


def get_hw_runtime_table(hw):
    """
    Creates hw runtime table according to the type of the hw

    :param hw: type of hw - ResourceDesc.TYPE (need to import from asap.strings)
    :return: HW runtime table dataframe

    Example::

            >>> table = get_hw_runtime_table(ResourceDesc.IP)
    """
    if hw == ResourceDesc.IP:
        data = AnalysisData.instance.ip_data
    elif hw == ResourceDesc.MEMORY:
        data = AnalysisData.instance.memory_data
    elif hw == ResourceDesc.BUS:
        data = AnalysisData.instance.bus_data
    else:
        raise ValueError("HW " + hw + " analysis is not supported!")

    return hw_runtime_table(data)


def get_hw_analysis(hw, start=0, end=None, intervals=1):
    """
    Creates hw run time and residency tables

    :param hw: Type of hw - ResourceDesc.TYPE (need to import from asap.strings)
    :param start: start time of the window
    :param end: end time of the window
    :param intervals: amount of intervals
    :return: HW runtime table dataframe, interval residency table dataframe
    """
    table = get_hw_runtime_table(hw)
    res = get_residency_table(table, start, end, intervals)
    return table, res


def hw_runtime_table(hw_trace):
    """
    Creates hw runtime table analysis with start and finish times of every resource
    + taking max overlapping working intervals

    :param hw_trace: list of HW_Events
    :return: HW runtime table dataframe
    """

    if not hw_trace:
        return DataFrame()

    analysis_data = list()
    start_times = dict()  # Dictionary to save resource to min start time for overlapping
    num_of_start = dict()  # Dictionary to save resource to number of times it started for overlapping
    num_of_finish = dict()  # Dictionary to save resource to number of times it ended for overlapping
    finish_times = dict()  # Dictionary to save resource to max finish time it ended for overlapping
    for event in hw_trace:
        name = event.RESOURCE
        if event.FINISH is NAN:
            if name not in num_of_start.keys():
                num_of_start[name] = 0
                start_times[name] = event.START
            num_of_start[name] += 1
        else:
            if event.RESOURCE not in num_of_finish.keys():
                num_of_finish[name] = 0
            num_of_finish[name] += 1
            event_finish = finish_times.get(name) if finish_times.get(name) is not None else 0
            finish_times[name] = max(event_finish, event.FINISH)
            if num_of_start[name] == num_of_finish[name]:
                analysis_data.append([start_times[name], finish_times[name], name,
                                      finish_times[name] - start_times[name]])
                del finish_times[name]
                del start_times[name]
                del num_of_finish[name]
                del num_of_start[name]

    # For unfinished resources, the finish time set to be the simulation timeout
    for name, start_time in start_times.items():
        analysis_data.append([start_times[name], AnalysisData.instance.simulation_time, name,
                              AnalysisData.instance.simulation_time - start_times[name]])

    return DataFrame(data=analysis_data, columns=[HW_EVENT_START, HW_EVENT_FINISH, HW_EVENT_RESOURCE,
                                                  HW_EVENT_DURATION])


def get_residency_table(table, start=0, end=None, intervals=1):
    """
    Makes hw residency analysis per interval

    :param table: hw runtime table dataframe
    :param start: start time of the window
    :param end: end time of the window
    :param intervals: amount of intervals
    :return: Interval residency table dataframe

    Example::

            >>> runtime_table = get_hw_runtime_table(ResourceDesc.IP)
            >>> residency_table = get_residency_table(runtime_table, start=0, end=500, intervals=5)
    """

    if table.empty:
        return DataFrame()
    if end is None:
        end = AnalysisData.instance.simulation_time
    if start < 0 or end < 0:
        raise ValueError('Start and end times cant be negative')

    if intervals == 0:
        raise ValueError('Intervals number must be > 0!')
    intervals = (end - start) / intervals

    event_names = table.RESOURCE.unique()
    time_names = create_time_column_list(start, end, intervals)
    analysis = DataFrame(0, index=event_names, columns=time_names, dtype=float)

    intervals_ranges = arange(start, end, intervals)
    for name, data in table.iterrows():
        name = data[HW_EVENT_RESOURCE]
        started = False
        init = data[HW_EVENT_START]
        finish = data[HW_EVENT_FINISH]
        if init < start:
            started = True
        for start_interval in intervals_ranges:
            if start_interval <= init <= start_interval + intervals:
                started = True
                if start_interval <= finish <= start_interval + intervals:
                    analysis[convert_time_to_name(start_interval, start_interval +
                                                  intervals)][name] += \
                        finish - init
                    break
                else:
                    analysis[convert_time_to_name(start_interval, start_interval +
                                                  intervals)][name] += start_interval + intervals - init

            elif started:
                if start_interval <= finish <= start_interval + intervals:
                    analysis[convert_time_to_name(start_interval, start_interval + intervals)][name] += \
                        finish - start_interval
                    break
                elif finish > start_interval + intervals:
                    analysis[convert_time_to_name(start_interval, start_interval + intervals)][name] += intervals

    return analysis / intervals * 100


def hw_analysis_to_excel(file_path, hw, intervals=1, start=0, end=AnalysisData.instance.simulation_time,
                         start_line=0, writer=None):
    """
    Creates excel file with relevant hardware analysis tables

    :param file_path: path of the excel file
    :param hw: type of hw, ResourceDesc.TYPE (need to import from asap.strings)
    :param intervals: amount of intervals for the interval table
    :param start: start time of the window for the window analysis
    :param end: end time of the window for the window analysis
    :param start_line: start line of the excel file to concatenate analysis
    :param writer: ExcelWriter object of the excel file to concatenate analysis
    :return: Number of lines that was written in the excel file
    """
    runtime, res = get_hw_analysis(hw, start, end, intervals)
    extension = 'xlsx'
    f, ext = os.path.splitext(file_path)
    if ext != extension:
        file_path = f + '.' + extension
    if writer is None:
        writer = ExcelWriter(file_path)
        workbook = writer.book
        worksheet = workbook.add_worksheet(HW_ANALYSIS)
        writer.sheets[HW_ANALYSIS] = worksheet
    else:
        worksheet = writer.sheets[HW_ANALYSIS]
        workbook = writer.book

    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    worksheet.write_string(start_line, 0, hw + ' runtime analysis', cell_format=title_format)
    start_line += 1
    runtime.to_excel(writer, sheet_name=HW_ANALYSIS, startrow=start_line, startcol=0)
    start_line += runtime.shape[0] + 2

    worksheet.write_string(start_line, 0, hw + ' interval residency analysis', cell_format=title_format)
    start_line += 1
    res.to_excel(writer, sheet_name=HW_ANALYSIS, startrow=start_line, startcol=0)
    start_line += res.shape[0] + 2

    return start_line, writer


def task_analysis_to_excel(file_path, start_line=0, writer=None):
    """
    Creates an excel file with task runtime analysis

    :param file_path: path of the excel file
    :param start_line: start line of the excel file
    :param writer: ExcelWriter object of the excel file
    :return: Number of lines that was written in the excel file
    """
    extension = 'xlsx'
    f, ext = os.path.splitext(file_path)
    if ext != extension:
        file_path = f + '.' + extension
    if writer is None:
        writer = ExcelWriter(file_path)

    workbook = writer.book
    worksheet = workbook.add_worksheet(TASK_ANALYSIS)
    writer.sheets['Task Analysis'] = worksheet

    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    worksheet.write_string(start_line, 0, 'Task runtime analysis', cell_format=title_format)
    start_line += 1
    AnalysisData.instance.task_table.to_excel(writer, sheet_name=TASK_ANALYSIS, startrow=start_line, startcol=0)
    start_line += AnalysisData.instance.task_table.shape[0] + 2

    return start_line, writer


def analysis_to_excel(file_path, start=0, end=None, intervals=1):
    """
    Dumps all analysis to excel file

    :param file_path:
    :param intervals: amount of intervals for the interval table
    :param start: start time of the window table
    :param end: end time of the window table
    """
    line = 0
    line, writer = hw_analysis_to_excel(file_path, ResourceDesc.IP, intervals, start, end, line)
    line, writer = hw_analysis_to_excel(file_path, ResourceDesc.MEMORY, intervals, start, end, line, writer)
    line, writer = hw_analysis_to_excel(file_path, ResourceDesc.BUS, intervals, start, end, line, writer)
    line, writer = task_analysis_to_excel(file_path, 0, writer)
    writer.save()


def analysis_to_html(file_path, start=0, end=None, intervals=1, custom_table_list=None):
    """
    Dumps all analysis to html file

    :param file_path:
    :param start: start time of tables
    :param end: end time of tables
    :param intervals: amount of intervals for tables
    :param custom_table_list: a list of dictionaries that represent custom tables and charts.
                              [ {'title': <title>, 'table': DataFrame,
                              'type': PIE_CHART/BAR_CHART/SCATTER_CHART/INTERVAL_CHART,
                              'data': [ (name, x list, y list,
                              *interval chart* - general y list - for y axis to have names ) ] } ]
    :return:
    """
    extension = 'html'
    f, ext = os.path.splitext(file_path)
    if ext != extension:
        file_path = f + '.' + extension
    ip_runtime_table, ip_residency_table = get_hw_analysis(ResourceDesc.IP, start=start, end=end, intervals=intervals)
    bus_runtime_table, bus_residency_table = \
        get_hw_analysis(ResourceDesc.BUS, start=start, end=end, intervals=intervals)
    mem_runtime_table, mem_residency_table = \
        get_hw_analysis(ResourceDesc.MEMORY, start=start, end=end, intervals=intervals)
    task_runtime_table = AnalysisData.instance.task_table
    sections = list()
    if not task_runtime_table.empty:
        sections.append(get_runtime_section(task_runtime_table, 'Task Runtime Table'))
    if not ip_runtime_table.empty:
        sections.append(get_runtime_section(ip_runtime_table, 'IP Runtime Table'))
    if not ip_residency_table.empty:
        sections.append(get_residency_section(ip_residency_table, 'IP Residency Table'))
    if not bus_runtime_table.empty:
        sections.append(get_runtime_section(bus_runtime_table, 'BUS Runtime Table'))
    if not bus_residency_table.empty:
        sections.append(get_residency_section(bus_residency_table, 'BUS Residency Table'))
    if not mem_runtime_table.empty:
        sections.append(get_runtime_section(mem_runtime_table, 'MEMORY Runtime Table'))
    if not mem_residency_table.empty:
        sections.append(get_residency_section(mem_residency_table, 'MEMORY Residency Table'))
    report = Report('Analysis', *sections)
    if custom_table_list is not None:
        try:
            for custom_table_dict in custom_table_list:
                data_list = [DataSeries(SPACE + info[0] + SPACE, x=info[1], y=info[2])
                             for info in custom_table_dict[DATA]]
                report.content.append(Section(custom_table_dict[TITLE],
                                              ContentGroup(Table(custom_table_dict[TABLE]),
                                                           custom_table_dict[TYPE](EMPTY, *data_list, sizehint=SMALL))))
        except KeyError:
            raise ValueError('Custom table list format is not supported! '
                             'Please see function documentation for format instructions.')
    render_report(report, file_path)


def get_runtime_section(runtime_table, title):
    """
    Returns Section object with the table and relevant chart

    :param runtime_table:
    :param title:
    :return: Section
    """
    return Section(title, Table(runtime_table),
                   IntervalChart(EMPTY, *[IntervalDataSeries(row['RESOURCE'], [row[START_COLUMN]],
                                                             [row['RESOURCE']],
                                                             [row['DURATION']]) for i, row in
                                          runtime_table.iterrows()],
                                 y_axis_ticks=list(runtime_table['RESOURCE']) if not runtime_table.empty else None,
                                 sizehint=SMALL))


def get_residency_section(residency_table, title):
    section = Section(title, Table(residency_table.reset_index()))
    if not residency_table.empty:
        section.content.append(BarChart(EMPTY, *[DataSeries(SPACE + row.name + SPACE, x=residency_table.keys(),
                                                            y=list(row)) for index, row in residency_table.iterrows()],
                                        sizehint=SMALL))
    return section


def upload_post_processing(platform_name: str, workload: str = '', comments: str = '', start=0, end=None,
                           intervals=1, custom_table_list=None):
    """
    Uploads post processing html file to conduit

    :param platform_name:
    :param workload:
    :param comments:
    :param start: start time of post processing
    :param end: end time of post processing
    :param intervals: number of intervals
    :param custom_table_list: a list of dictionaries that represent custom tables and charts.
                              [{'title': <title>, 'table': DataFrame,
                              'type': PIE_CHART/BAR_CHART/SCATTER_CHART/INTERVAL_CHART,
                              'data': [ (name, x list, y list, *interval chart* -
                              general y list - for y axis to have names  ] } ]
    :return:
    """
    pass


def upload_results_file(file_path, platform_name: str, workload: str = '', comments: str = ''):
    """
    Uploads html results file to conduit

    :param platform_name:
    :param file_path: the file path to upload
    :param workload:
    :param comments:
    :return:
    """
    pass


def convert_time_to_name(start, finish):
    return '{0:.2f}-{1:.2f}'.format(start, finish)


def create_time_column_list(start, end, window_size):
    """
    Creates list of time strings ['start_time-end_time', ...]

    :param start:
    :param end:
    :param window_size:
    :return:
    """
    time_names = list()
    for start_interval in arange(start, end, window_size):
        if start_interval + window_size > end:
            col_name = convert_time_to_name(start_interval, end)
        else:
            col_name = convert_time_to_name(start_interval, start_interval + window_size)
        time_names.append(col_name)
    return time_names


def create_states_residency(states, sim_time, intervals=1):
    from asap.defaults import ActiveStates
    from asap.buses import Bus
    from asap.memories import Memory
    # Resources starts with C0 state, adding C0 state at 0 time.

    resources = states.RESOURCE.unique()
    data = []
    for resource in resources:
        if isinstance(resource, Bus) or isinstance(resource, Memory):
            data.insert(0, {'TIME': 0.0, 'RESOURCE': resource, 'STATE': ActiveStates.ACTIVE_STATE})
    states = concat([DataFrame(data), states], ignore_index=True)

    # Adding FINISH column to states
    import numpy as np
    state_start_finish = DataFrame()
    for resource in resources:
        resource_data = states[states['RESOURCE'] == resource].rename(columns={'TIME': START_COLUMN})
        resource_data = resource_data.reset_index(drop=True)
        resource_data[FINISH_COLUMN] = resource_data[START_COLUMN].shift(-1)
        resource_data = resource_data[resource_data[START_COLUMN] != resource_data[FINISH_COLUMN]]
        state_start_finish = concat([state_start_finish, resource_data])
    state_start_finish = state_start_finish.replace(np.nan, sim_time).reset_index(drop=True)[
        [START_COLUMN, FINISH_COLUMN, 'RESOURCE', 'STATE']]

    # STATES residency of each resource and state
    resources_states = state_start_finish
    resources_states['RESOURCE'] = resources_states['RESOURCE'].map(str) + "_" + resources_states['STATE']
    resources_states_residency = get_residency_table(state_start_finish, end=sim_time, intervals=intervals)
    return resources_states_residency


def create_residency_table(table, object_titles_list, start=0, end=None, intervals=1):
    """
    Creates a residency table for the object that matches the relevant values

    :param table: the table need to be start and end times table
    :param start:
    :param end:
    :param intervals:
    :param object_titles_list: the object titles that we want to create the residencies for
    :return:

    Example::

            >>> runtime_table = DataFrame(columns['TIME', 'RESOURCE'])
            >>> residency_table = create_residency_table(runtime_table, start=0, end=500, intervals=5)
    """
    table['RESOURCE'] = table[object_titles_list[0]].astype(str)
    if len(object_titles_list) > 1:
        for obj_title in object_titles_list[1:]:
            table['RESOURCE'] += "_" + table[obj_title].astype(str)
    res_table = get_residency_table(table, start=start, end=end, intervals=intervals)
    return res_table


def get_average_value_table(interval_table, object_title, value_title, start=0, end=None, intervals=1):
    """
    Gets the average value of given interval table by object title and value title
    Table assumptions - START, FINISH, and the object title and value title columns

    :param interval_table: runtime table with objects and values
    :param object_title: the column title of the objects you want to return their avg value
    :param value_title: the column title of the value that you want to calculate it's avg
    :param start:
    :param end:
    :param intervals:
    :return: average value table by object
    """
    if interval_table.empty:
        return DataFrame()
    if end is None:
        end = AnalysisData.instance.simulation_time
    if start < 0 or end < 0:
        raise ValueError('Start and end times cant be negative')

    if intervals == 0:
        raise ValueError('Intervals number must be > 0!')

    interval_range = (end - start) / intervals

    names = interval_table[object_title].unique()
    time_columns = create_time_column_list(start, end, interval_range)
    avg_value_results = DataFrame(0, index=names, columns=time_columns, dtype=float)

    times_intervals_list = arange(start, end, interval_range)
    for idx, row in interval_table.iterrows():
        name = row[object_title]
        started = False
        current_start = row[START_COLUMN]
        current_finish = row[FINISH_COLUMN]
        value = row[value_title]
        if current_start < start:
            started = True
        for start_interval in times_intervals_list:
            if start_interval <= current_start <= start_interval + interval_range:
                started = True
                if start_interval <= current_finish <= start_interval + interval_range:
                    avg_value_results[convert_time_to_name(start_interval, start_interval + interval_range)][name] += \
                        value * (current_finish - current_start)
                    break
                else:
                    avg_value_results[convert_time_to_name(start_interval, start_interval + interval_range)][name] += \
                        value * (start_interval + interval_range - current_start)

            elif started:
                if start_interval <= current_finish <= start_interval + interval_range:
                    avg_value_results[convert_time_to_name(start_interval, start_interval + interval_range)][name] += \
                        value * (current_finish - start_interval)
                    break
                elif current_finish > start_interval + interval_range:
                    avg_value_results[convert_time_to_name(start_interval, start_interval + interval_range)][name] += \
                        value * interval_range

    return avg_value_results / interval_range


def convert_heartbeat_to_interval_table(table, object_titles, value_title=None):
    """
    Converts heartbeat table to interval table - assumption TIME column

    :param table: heartbeat table - table with no start and finish times, only what happened at a certain point in time
    :param object_titles: a list with the objects to want to set it's start and finish times
    :param value_title: a value title to match the object
    :return:
    """
    from .setup import OBJECT_NAME_SEPERATOR
    if value_title is None:
        return convert_heartbeat_to_interval_table_by_object(table, object_titles[0])
    table_intervals = list()
    obj_to_value = dict()
    obj_to_start_time = dict()
    for index, row in table.iterrows():
        # connecting the names of all of the objects into one name (if there are more than one object_title in the list)
        obj_name = None
        for object_title in object_titles:
            if obj_name is None:
                obj_name = row[object_title]
            else:
                obj_name += OBJECT_NAME_SEPERATOR + row[object_title]

        last_value = obj_to_value.get(obj_name, None)
        if last_value is None:
            obj_to_start_time[obj_name] = row[TIME_COLUMN]
            obj_to_value[obj_name] = row[value_title]
            continue
        if obj_to_value[obj_name] == row[value_title]:
            continue
        table_intervals.append([obj_to_start_time[obj_name], row[TIME_COLUMN],
                                *[row[object_title] for object_title in object_titles], obj_to_value[obj_name]])
        obj_to_start_time[obj_name] = row[TIME_COLUMN]
        obj_to_value[obj_name] = row[value_title]

    # Adds the last rows and completes them to the end of the simulation
    for obj_name, start_time in obj_to_start_time.items():
        obj_names = obj_name.split(OBJECT_NAME_SEPERATOR)
        table_intervals.append([start_time, AnalysisData.instance.simulation_time, *obj_names, obj_to_value[obj_name]])
    columns = [START_COLUMN, FINISH_COLUMN, *[object_title for object_title in object_titles], value_title]
    return DataFrame(data=table_intervals, columns=columns).sort_values(by=[START_COLUMN,
                                                                            FINISH_COLUMN]).reset_index(drop=True)


def convert_heartbeat_to_interval_table_by_object(table, object_title):
    """
    converts heartbeat tables to start and finish times table by object only

    :param table: heartbeat table - table with no start and finish times, only what happened at a certain point in time
    :param object_title: the object title
    :return:
    """
    import numpy as np
    if not object_title:
        return DataFrame()
    objects = table[object_title].unique()
    start_finish_table = DataFrame()
    for obj in objects:
        table_data = table[table[object_title] == obj].rename(columns={'TIME': START_COLUMN})
        table_data = table_data.reset_index(drop=True)
        table_data[FINISH_COLUMN] = table_data[START_COLUMN].shift(-1)
        table_data = table_data[table_data[START_COLUMN] != table_data[FINISH_COLUMN]]
        start_finish_table = concat([start_finish_table, table_data])
    return start_finish_table.replace(np.nan, AnalysisData.instance.simulation_time).sort_values(
        by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)


def create_analysis_comparison(exp_path, output_file_path):
    """
    Creates analysis comparison between different experiments.

    :param: exp_path: The path of the csv results files, please note that it should be in the following format:
                      There should be a folder for every experiment with the name of the experiment,
                      inside each experiment folder should be the csv files according to the analysis.
                      For example if there is a table of 'memory_bw' than there should be a csv file named
                      memory_bw inside the relevant experiments folders, the comparison will happen on the
                      files with the same name in the different experiment folder.
                      Please note that only one column tables are supported.
                      TODO: Add multiple column option
    :param: output_file_path: A path to the output html file with html format
    """
    from .tables import combine_dataframes
    processed_results = dict()
    results_titles = set()
    exp_list = list()
    for foldername in os.listdir(exp_path):
        if os.path.isdir(os.path.join(exp_path, foldername)):
            exp_list.append(foldername)

    # Creates the results titles
    for exp in exp_list:
        for filename in os.listdir(os.path.join(exp_path, exp)):
            if filename.endswith('.csv'):
                results_titles.add(filename.replace('.csv', ''))

    # Collecting the data from the experiments folders
    for exp in exp_list:
        for result_title in results_titles:
            result_file_name = result_title + '.csv'
            if os.path.isfile(os.path.join(exp_path, exp, result_file_name)):
                result_df = read_csv(os.path.join(exp_path, exp, result_file_name), index_col=0, skiprows=0)
                if len(result_df.columns) > 1:
                    raise ValueError('Only one column tables are supported in comparison right now: ' + result_title)
                result_df.columns = ['Value']
                result_df.index.name = 'Resource'
            else:
                # This kind of analysis doesn't exist in the experiment
                continue
            if processed_results.get(result_title) is None:
                processed_results[result_title] = dict()
            processed_results[result_title].update({exp: result_df})

    sections = list()

    # Comparison between different experiments results
    for result_title in results_titles:
        current_result_dict = dict()
        current_result_charts = list()
        for exp_name in exp_list:
            processed_result = processed_results[result_title].get(exp_name)
            if processed_result is None:
                continue
            current_result_dict[exp_name] = processed_result

        comparison_df = combine_dataframes(current_result_dict)
        for index, row_data in comparison_df.iterrows():
            dss = [
                DataSeries(exp_name, x=[result_title + ' value'], y=[row_data[('Value', exp_name)]])
                for exp_name in exp_list if processed_results[result_title].get(exp_name) is not None
            ]
            chart = BarChart(row_data[0], *dss)
            current_result_charts.append(chart)

        current_result_section = Section(result_title, Table(comparison_df))
        for chart in current_result_charts:
            current_result_section.content.append(Section(chart.title, chart))

        sections.append(current_result_section)

        report = Report('Result Comparison', *sections)
        render_report(report, output_file_path)
