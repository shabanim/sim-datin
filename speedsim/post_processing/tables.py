from bokeh.layouts import Spacer, column, row
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, Div, Select, TableColumn
from pandas import DataFrame, MultiIndex, concat

from asap.strings import AND, OR

from .setup import (AND_SIGN, CLOSE_BRACKET, COLON, COMMA, EXPRESSION,
                    FINISH_COLUMN, OPEN_BRACKET, OR_SIGN, START_COLUMN,
                    TIME_COLUMN)


class InteractiveTableLayout:
    ALL_VALUES = 'All Values'
    GREEN_BACKGROUND_TEXT_STYLE = {'font-weight': 'bold', 'color': 'white', 'background-color': '#4CAF50',
                                   'padding-left': '5px', 'padding-right': '5px'}
    COLUMN_WIDTH = 170

    def __init__(self, title, table):
        # data frame
        self._dataframe_table = table.astype(str)

        # sku's table
        self._interactive_table_source = ColumnDataSource(self._dataframe_table)
        self._interactive_table_columns = [TableColumn(field=col, title=col, width=self.COLUMN_WIDTH) for col in
                                           self._dataframe_table.columns]

        self._interactive_table = DataTable(columns=self._interactive_table_columns,
                                            source=self._interactive_table_source,
                                            width=self.COLUMN_WIDTH*len(self._interactive_table_columns)+40)

        # filtering
        self.__create_text_filters(table.columns)

        # create title
        self._title_div = Div(text=title, style=self.GREEN_BACKGROUND_TEXT_STYLE)

        # create the layout
        self.layout = column(self._title_div, row(self.__text_filters), row(self._interactive_table))

    def __create_text_filters(self, text_filter_columns):
        first_space = Spacer(width=43)
        self.__text_filters = [first_space]
        for filter_column in text_filter_columns:
            column_values = list(set(self._dataframe_table[filter_column].values))
            column_values.sort()
            column_values.insert(0, self.ALL_VALUES)
            select_column_value = Select(title=filter_column, value=self.ALL_VALUES, options=column_values,
                                         width=self.COLUMN_WIDTH-13)
            select_column_value.on_change('value', self.__on_text_filter_change(filter_column))
            self.__text_filters.append(select_column_value)

    def __on_text_filter_change(self, col):
        def on_change(attr, old, new):
            if new != old:
                self.__apply_filters()

        return on_change

    def __apply_filters(self):
        filtered_skus_df = self.__calculate_filtered_df(self.__text_filters)
        self._interactive_table_source = ColumnDataSource(filtered_skus_df)

        self._interactive_table.source = self._interactive_table_source

        self.__update_text_filters_options()

    def __update_text_filters_options(self):
        for text_filter in self.__text_filters:
            if not isinstance(text_filter, Spacer):
                text_filter_options = self.__calculate_text_filters_options(text_filter)
                text_filter.options = text_filter_options

    def __calculate_text_filters_options(self, text_filter):
        other_filters = filter(lambda f: f != text_filter, self.__text_filters)
        filtered_df = self.__calculate_filtered_df(other_filters)
        filter_options = list(set(filtered_df[text_filter.title].values))
        filter_options.sort()
        filter_options.insert(0, self.ALL_VALUES)
        return filter_options

    def __calculate_filtered_df(self, text_filters):
        filtered_skus_df = self._dataframe_table
        for text_filter in text_filters:
            if not isinstance(text_filter, Spacer) and text_filter.value != self.ALL_VALUES:
                filtered_skus_df = filtered_skus_df[filtered_skus_df[text_filter.title] == text_filter.value]
        return filtered_skus_df


def show_interactive_table(table, table_name=''):
    """
    Shows the table with sorting and filtering options

    :param table: dataframe
    :param table_name: the name of the table

    Example::

            >>> table = DataFrame()
            >>> show_interactive_table(table, 'table_name')
    """
    from bokeh.application import Application
    from bokeh.application.handlers import FunctionHandler
    from notebook import notebookapp
    from bokeh.io import show
    import os

    def modify_doc(doc):
        table_manager = InteractiveTableLayout(table_name, table)
        doc.add_root(table_manager.layout)
        return doc

    # Set up an application to show in the notebook
    handler = FunctionHandler(modify_doc)
    app = Application(handler)
    servers = list(notebookapp.list_running_servers())
    port = servers[0]['port']  # TODO: need to get the relevant port to the one we're working on
    cmd = 'hostname'
    host = os.popen(cmd).read().rstrip()
    cmd = 'hostname -d'
    domain = os.popen(cmd).read().rstrip()
    url = 'http://' + host + '.' + domain + ':' + str(port)
    show(app, notebook_url=url)


def find_bubbles(res, hw_resource, start, end):
    """
    Finding bubbles in time range given of hw resource.
    Expected task analysis results to have START/FINISH/RESOURCE columns

    :param res: Task analysis results
    :param hw_resource:
    :param start:
    :param end:
    :return: True, first time bubble happen if there is bubble, False and None otherwise.
    """
    from pnets.simulation import SIM_EVENT_START, SIM_EVENT_FINISH, SIM_EVENT_RESOURCE
    prev_end = None
    for idx, row_data in res.iterrows():
        if row_data[SIM_EVENT_START] < start or row_data[SIM_EVENT_FINISH] > end or row_data[SIM_EVENT_RESOURCE] != \
                hw_resource:
            continue
        if prev_end is None:
            prev_end = row_data[SIM_EVENT_FINISH]
        else:
            if row_data[SIM_EVENT_START] > prev_end:
                return True, row_data[SIM_EVENT_START]
            prev_end = row_data[SIM_EVENT_FINISH]
    return False, None


def merge_columns(table, title1, title2):
    """
    Merges the title2 column into title1 puts '_' between the values names, and deletes the title2 column

    :param table:
    :param title1:
    :param title2:
    :return:
    """
    table[title1] = table[title1].map(str) + "_" + table[title2].map(str)
    del table[title2]
    return table


def add_zero_instances_to_table(table, object_title, default_values_dict):
    """
    Adds zero instances to heartbeat table by object title
    Table assumptions: TIME column

    :param table: heartbeat table - table with no start and finish times, only what happened at a certain point in time
    :param object_title: he column title of the objects you want to add zero time instances
    :param default_values_dict: dictionary with titles and default values, example: {'BW': 6400}
    :return:
    """
    objects = table[object_title].unique()
    data = []
    for obj in objects:
        titles = {TIME_COLUMN: 0.0}
        titles.update(default_values_dict)
        titles.update({object_title: obj})
        data.insert(0, titles)
    return concat([DataFrame(data), table], ignore_index=True, sort=True)


def get_intersection_times_between_objects(table, object_title, output_obj_name):
    """
    Returns runtime table intersection times between objects
    Checks when all of the objects (in the object_title column) in the table are working at once
    (have the same time frame) and returns a table with the intersections times

    :param table: Expected to get table with start and finish times columns
    :param object_title: the column title of the objects you want to return their intersection
    :param output_obj_name: name of the object after the intersection which will be showed in the outputted table
    :return: intersections times Dataframe
    """
    objects = table[object_title].unique()

    intervals = None
    for obj in objects:
        obj_data = table[(table[object_title] == obj)]
        if intervals is None:
            intervals = list()
            for index, row_data in obj_data.iterrows():
                intervals.append([row_data[START_COLUMN], row_data[FINISH_COLUMN], output_obj_name])
        else:
            overlapped_intervals = []
            for index, row_data in obj_data.iterrows():
                for interval in intervals:
                    if row_data[FINISH_COLUMN] < interval[0] or interval[1] < row_data[START_COLUMN]:
                        continue
                    else:
                        start_time = max(interval[0], row_data[START_COLUMN])
                        end_time = min(interval[1], row_data[FINISH_COLUMN])
                        overlapped_intervals.append([start_time, end_time, output_obj_name])
            intervals = overlapped_intervals

    result_table = DataFrame(intervals, columns=[START_COLUMN, FINISH_COLUMN, object_title])
    return result_table.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)


def get_union_table(table, object_title):
    """
    Removing overlapping times in start and end times of the same object and extends the times to the longest time
    Table assumption

    :param table:
    :param object_title: the column title of the object
    :return:
    """
    objects = table[object_title].unique()
    result_table = DataFrame()
    for obj in objects:
        obj_data = table[(table[object_title] == obj)]
        obj_data = obj_data.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)
        start_time = None
        end_time = None
        overlapped_intervals = list()
        for index, row_data in obj_data.iterrows():
            if start_time is None:
                start_time = row_data[START_COLUMN]
                end_time = row_data[FINISH_COLUMN]
                continue
            if start_time <= row_data[START_COLUMN] <= end_time:
                end_time = max(end_time, row_data[FINISH_COLUMN])
            else:
                overlapped_intervals.append([start_time, end_time, obj])
                start_time = row_data[START_COLUMN]
                end_time = row_data[FINISH_COLUMN]
        overlapped_intervals.append([start_time, end_time, obj])
        result = DataFrame(overlapped_intervals, columns=[START_COLUMN, FINISH_COLUMN, object_title])
        result_table = concat([result_table, result])

    return result_table.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)


def get_intersection_table(table, object_title):
    """
    Gets the intersection times of the same object (by the object_title)

    :param table: expected to be table with start and finish times
    :param object_title: the column title of the objects you want to return their intersection
    :return: intersections times Dataframe
    """
    objects = table[object_title].unique()
    result_table = DataFrame()
    for obj in objects:
        obj_data = table[(table[object_title] == obj)]
        obj_data = obj_data.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)
        start_time = None
        end_time = None
        overlapped_intervals = list()
        for index, row_data in obj_data.iterrows():
            if start_time is None:
                start_time = row_data[START_COLUMN]
                end_time = row_data[FINISH_COLUMN]
                continue
            if row_data[START_COLUMN] < end_time:
                start_time = max(row_data[START_COLUMN], start_time)
                end_time = min(row_data[FINISH_COLUMN], end_time)
            else:
                overlapped_intervals.append([start_time, end_time, obj])
                start_time = row_data[START_COLUMN]
                end_time = row_data[FINISH_COLUMN]
        overlapped_intervals.append([start_time, end_time, obj])
        result = DataFrame(overlapped_intervals, columns=[START_COLUMN, FINISH_COLUMN, object_title])
        result_table = concat([result_table, result])

    return result_table.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)


def filter_table_by_expression(table, expression):
    """
    Returns the table filtered by the expression_dict

    :param table: expected to be table with start and finish times
    :param expression: {<object>:<value>}
    :return:
    """
    conditional_res = table[create_condition_for_dataframe(table, expression)]
    return conditional_res.sort_values(by=[START_COLUMN, FINISH_COLUMN]).reset_index(drop=True)


def create_condition_for_dataframe(table, expression):
    """
    Creates a condition for dataframe

    :param table:
    :param expression: {<object>:<value>}
    :return: condition for Dataframe
    """
    condition = None
    for title, value in expression.items():
        condition_to_add = (table[title] == value)
        if condition is None:
            condition = condition_to_add
        else:
            condition = condition & condition_to_add
    return condition


def get_condition_name(expression):
    """
    Returns a string that represents the expression

    :param expression:
    :return:
    """
    conditions = expression.get(OR, None)
    is_and_condition = False
    if conditions is None:
        conditions = expression.get(AND, None)
        is_and_condition = True
    if conditions is None:
        condition = ''
        for key, value in expression.items():
            condition += key + COLON + ' ' + str(value)
        return condition
    condition = None
    for condition_desc_list in expression.values():
        for condition_desc in condition_desc_list:
            for obj, value in condition_desc.items():
                if obj == AND or obj == OR:
                    condition_to_add = OPEN_BRACKET + get_condition_name({obj: value}) + CLOSE_BRACKET
                else:
                    condition_to_add = OPEN_BRACKET + obj + COLON + ' ' + str(value) + CLOSE_BRACKET
                if condition is None:
                    condition = condition_to_add
                else:
                    if is_and_condition:
                        condition += ' and ' + condition_to_add
                    else:
                        condition += ' or ' + condition_to_add
    return condition


def get_concurrency_table(table, expression, expression_name='Expression'):
    """
    Returns a merged table that contains the intervals when expression is true in the given table

    :param table:
    :param expression: {'OR'/'AND': [{<title>:<value>, <title>:<value>}, {'OR'/'AND': [...]}]}.
                       please note that if the expression is a string the function will convert it to dictionary style
                       also all of the conditions that are inside one dictionary are with "and" logic inside
                       the filtered table the 'AND/OR' in the dictionary keys represents
                       the time intersections or unions and not and on the table title and values
                       example for a string: '|(<title>: <value>, <title>: <value>)'
    :param expression_name: the expression name that will show in the outputted table
    :return:

    Example::

            >>> table = DataFrame()
            >>> get_concurrency_table(table, {'AND': [{'RESOURCE': 'Display'}, {'BW': 6400}]})
    """
    if isinstance(expression, str):
        raise ValueError('Currently str expressions are not supported!')
        # expression = convert_string_expression_to_dict(expression)
    elif isinstance(expression, LogicExpression):
        expression = convert_expression_to_dict(expression)
    table = get_table_by_expression(table, expression)
    if table.empty:
        return DataFrame()
    table[EXPRESSION] = expression_name
    return get_union_table(table, EXPRESSION)


def get_table_by_expression(table, expression):
    """
    Gets the table by the expression, does overlapping for AND conditions and concatenates for OR conditions

    :param table:
    :param expression: {'OR'/'AND': [{<title>:<value>}, {'OR'/'AND': [...]}]}
    :return: filtered table by the expression
    """
    new_table = DataFrame(columns=[EXPRESSION, START_COLUMN, FINISH_COLUMN])
    key = list(expression.keys())[0]
    if key != AND and key != OR:
        new_table = concat([new_table, filter_table_by_expression(table, expression)], sort=True)
    elif key == AND:
        for condition in expression[key]:
            new_table = concat([new_table, get_table_by_expression(table, condition)], sort=True)
        new_table = get_intersection_times_between_objects(new_table, EXPRESSION, get_condition_name(expression))
    else:
        for condition in expression[key]:
            new_table = concat([new_table, get_table_by_expression(table, condition)], sort=True)

    new_table[EXPRESSION] = get_condition_name(expression)
    return new_table


def convert_string_expression_to_dict(expression: str):
    """
    Converts a string to the dictionary format expression

    :param expression: should be in the following format: '&(<obj>:<val>, <obj>:<val>, |(<obj>:<val>, <obj>:<val>))

    :return:
    """
    # TODO: Need to be supported with the new format
    expression = expression.replace(' ', '')
    if AND_SIGN not in expression and OR_SIGN not in expression:
        raise ValueError('The string format is not supported, there needs to be |/& before every set of obj:val')
    else:
        dict_list = list()
        conditions = expression.split(OPEN_BRACKET, 1)
        conditions = conditions[1]
        conditions = conditions.rsplit(CLOSE_BRACKET, 1)
        conditions = conditions[0]
        still_parsing = True
        while still_parsing:
            if not conditions.startswith(AND_SIGN) and not conditions.startswith(OR_SIGN):
                conditions = conditions.split(COMMA, 1)
                condition = conditions[0].split(COLON, maxsplit=1)
                dict_list.append({condition[0]: condition[1]})
                if len(conditions) == 1:
                    break
                conditions = conditions[1]
            else:
                count_of_open = 0
                count_of_close = 0
                last_close = 0
                for i in range(0, len(conditions)):
                    if conditions[i] == OPEN_BRACKET:
                        count_of_open += 1
                    elif conditions[i] == CLOSE_BRACKET:
                        count_of_close += 1
                        last_close = i
                    if count_of_open == count_of_close and count_of_open != 0:
                        if last_close == len(conditions) - 1:
                            dict_list += [convert_string_expression_to_dict(conditions)]
                            still_parsing = False
                        else:
                            dict_list += [convert_string_expression_to_dict(conditions[:last_close + 1])]
                            conditions = conditions[last_close+2:]
                        break

        if expression.startswith(AND_SIGN):
            return {AND: dict_list}
        elif expression.startswith(OR_SIGN):
            return {OR: dict_list}
        else:
            raise ValueError('The expression format is not supported, please see documentation for more details.')


#  Expressions API for concurrency tables
class LogicExpression:
    def __init__(self, conditions: list, logic: str = AND):
        """
        Defines Logic Expression among expressions/conditions

        :param conditions: list of dict or expressions
                           the dictionary should be: {title: value}
        :param logic: the logic between the conditions (AND or OR)
        """
        self._conditions = conditions
        self._logic = logic

    @property
    def conditions(self):
        return self._conditions

    @conditions.setter
    def conditions(self, conditions):
        self._conditions = conditions

    @property
    def logic(self):
        return self._logic

    def add_condition(self, condition):
        self._conditions.append(condition)


class LogicCondition:
    def __init__(self, title, value):
        """
        :param title: title of the value
        :param value: the value that you want to match the title
                      For example in states: title = 'STATE', value = 'C0'
        """
        self._object_name = title
        self._value = value

    @property
    def object_name(self):
        return self._object_name

    @object_name.setter
    def object_name(self, object_name):
        self._object_name = object_name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


def convert_expression_to_dict(expression: LogicExpression):
    """
    :param expression: LogicExpression
    :return: dictionary
    """
    conditions = list()
    for condition in expression.conditions:
        if isinstance(condition, LogicExpression):
            conditions.append(convert_expression_to_dict(condition))
        elif isinstance(condition, LogicCondition):
            conditions.append({condition.object_name: condition.value})
        elif isinstance(condition, dict):
            conditions.append(condition)
        else:
            raise ValueError('The conditions of LogicExpression need to be either'
                             ' LogicExpression, LogicCondition or Dictionary!')

    return {expression.logic: conditions}


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

    merged = DataFrame(columns=MultiIndex.from_tuples(multi_index))
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
