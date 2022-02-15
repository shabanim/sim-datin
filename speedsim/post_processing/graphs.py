from itertools import cycle

from bokeh.events import DoubleTap, MouseMove
from bokeh.layouts import Column, GridBox, Spacer, column, gridplot, row
from bokeh.models import (Button, ColumnDataSource, CrosshairTool, CustomJS,
                          Label, Span, TextInput)
from bokeh.palettes import Category20
from bokeh.plotting import Figure, figure
from bokeh.plotting.helpers import _get_range, _get_scale
from bokeh.transform import dodge
from pandas import DataFrame

from post_processing.setup import FINISH_COLUMN, START_COLUMN


def connect_graphs(graph_list, gridplot_list=None, x_range=None):
    """
    Connects graphs x_range for comparison

    :param graph_list: list of bokeh layouts or figures
                       (if the layouts are gridplot or column it will connect the inner figures)
    :param gridplot_list: the generated list for gridplot for recursion
    :param x_range: x_range for recursion
    :return:
    """
    first_level = False
    if gridplot_list is None:
        gridplot_list = list()
        first_level = True
    for graph in graph_list:
        if isinstance(graph, Figure):
            x_range = change_figure_x_range(graph, x_range)
            gridplot_list.append([graph])
        elif isinstance(graph, list):
            x_range, gridplot_list = connect_graphs(graph, gridplot_list, x_range)
        elif isinstance(graph, Column) or isinstance(graph, GridBox):
            x_range, gridplot_list = connect_graphs(graph.children, gridplot_list, x_range)
        else:
            gridplot_list.append([graph])

    if first_level:
        return gridplot(gridplot_list)
    else:
        return x_range, gridplot_list


def change_figure_x_range(fig, x_range=None):
    """
    Changes the x_range of the figure according to the x_range input

    :param fig: bokeh figure
    :param x_range:
    :return: x_range
    """
    if x_range is None:
        x_range = fig.x_range
    else:
        fig.x_range = x_range
    return x_range


def resources_interval_graph(fig, results, colors=None):
    """
    Display lanes with resources

    :param fig: bokeh figure
    :param results: resources run time table
    :param colors: if specified, provides a map of transition name to color
    """
    # TODO: Saeed & Or think of general function for interval graphs
    if colors is None:
        colors = {}
    palette = cycle(Category20[20])

    resources = results.RESOURCE.unique()
    ticks = ["{}".format(r) for r in resources]
    fig.y_range = _get_range(ticks)
    fig.y_scale = _get_scale(fig.y_range, 'auto')

    # figure.x_range = resources
    rectangles = []

    for start, finish, resource in results[[START_COLUMN, FINISH_COLUMN, 'RESOURCE']].itertuples(index=False):
        if resource in colors:
            color = colors[resource]
        else:
            color = next(palette)
            colors[resource] = color

        rectangles.append((start, finish, '{}'.format(resource), color, resource, finish - start))

    rectangles = DataFrame(rectangles, columns=['left', 'right', 'lane', 'color', 'NAME', 'duration'])
    src = ColumnDataSource.from_df(rectangles)
    fig.quad(source=src, left='left', right='right', bottom=dodge('lane', -0.45, range=fig.y_range),
             top=dodge('lane', +0.45, range=fig.y_range), color='color')


def create_resource_fig(results):
    """
    Creates bokeh figure for resource runtime results

    :param results: Dataframe of resource runtime
    :return: Bokeh Figure

    Example::

            >>> table = DataFrame(columns=['TIME', 'RESOURCE'])
            >>> fig = create_resource_fig(table)
    """
    if results.empty:
        return figure()
    ys = results.RESOURCE.unique()
    fig = figure(title='Time: ', plot_width=1000, plot_height=800, tools=['xpan', 'xwheel_zoom'],
                 active_scroll='xwheel_zoom', y_range=ys,
                 tooltips=[('name', '@NAME'), ('start', '@left'), ('finish', '@right'), ('duration', '@duration')])
    resources_interval_graph(fig, results)
    fig = add_two_interactive_lines(fig)
    return fig


class LineInfo:
    """
    Distinguish wether we need to move the blue line or the red line for the two interactive lines
    """
    def __init__(self):
        self.line = 1

    def __dict__(self):
        return


def add_two_interactive_lines(fig):
    """
    Adds two interactive lines to bokeh figure, when double click on figure you can move the lines

    :param fig: Bokeh Figure
    :return: Bokeh Column
    """
    blue_line = Span(dimension='height', line_color='blue')
    red_line = Span(dimension='height', line_color='red')
    blue_line_label = Label(x=0, y=0, y_units='screen', text='')
    red_line_label = Label(x=0, y=0, y_units='screen', text='')
    choose_line = {'line': 1}
    button = Button(label="Clear Lines", width=20, height=30)
    text_input = TextInput(value="", title='Enter line time: ', width=150)

    text_input.js_on_change('value', CustomJS(args=dict(blue_line=blue_line, blue_line_label=blue_line_label,
                                                        red_line=red_line, red_line_label=red_line_label,
                                                        choose_line=choose_line, fig=fig), code="""
                                                            var time = parseFloat(cb_obj.value)
                                                            if(choose_line.line == 1){
                                                                blue_line.location = time;
                                                                blue_line_label.x = time;
                                                                blue_line_label.text = time.toFixed(2).toString();
                                                                choose_line.line = 2;
                                                            }
                                                            else{
                                                                red_line.location = time;
                                                                red_line_label.x = time;
                                                                red_line_label.text = time.toFixed(2).toString();
                                                                choose_line.line = 1;
                                                            }
                                                            fig.change.emit()

                                                       """))
    fig.add_layout(blue_line_label)
    fig.add_layout(red_line_label)
    fig.add_layout(blue_line)
    fig.add_layout(red_line)
    cross = CrosshairTool(dimensions='height')
    fig.add_tools(cross)
    fig.js_on_event(DoubleTap, CustomJS(args=dict(blue_line=blue_line, blue_line_label=blue_line_label,
                                                  red_line=red_line, red_line_label=red_line_label,
                                                  choose_line=choose_line), code="""
            if(choose_line.line == 1){
                blue_line.location = cb_obj.x;
                blue_line_label.x = cb_obj.x;
                blue_line_label.text = cb_obj.x.toFixed(2).toString();
                choose_line.line = 2;
            }
            else{
                red_line.location = cb_obj.x;
                red_line_label.x = cb_obj.x;
                red_line_label.text = cb_obj.x.toFixed(2).toString();
                choose_line.line = 1;
            }

        """))

    fig.js_on_event(MouseMove, CustomJS(args=dict(title=fig.title, blue_line=blue_line, red_line=red_line), code="""
            var diff_between_lines = Math.abs(blue_line.location - red_line.location).toFixed(2).toString();
            var main_line = cb_obj.x.toFixed(2).toString();
            var diff_to_red = Math.abs(cb_obj.x - red_line.location).toFixed(2).toString();
            var diff_to_blue = Math.abs(cb_obj.x - blue_line.location).toFixed(2).toString();
            title.text = "Time: " + main_line + " us,        Diff to blue: " + diff_to_blue +
                            ",        Diff to red: " + diff_to_red +
                            ",        Diff between static lines: " + diff_between_lines;
        """))

    button.callback = CustomJS(args=dict(blue_line=blue_line, red_line=red_line,
                                         blue_line_label=blue_line_label, red_line_label=red_line_label,
                                         fig=fig), code="""
            blue_line.location = -1000;
            blue_line_label.x = -1000;
            blue_line_label.text = "";
            red_line_label.x = -1000;
            red_line_label.text = "";
            red_line.location = -1000;
            fig.change.emit();
    """)

    text_and_button_space = Spacer(width=fig.plot_width - text_input.width - button.width)
    return column(row(text_input, text_and_button_space, button), fig)


def create_states_figs(results):
    """
    Creates bokeh figure for states runtime results
    :param results:
    :return: Bokeh Figure

    Example::

            >>> table = DataFrame(columns=['RESOURCE', 'TIME', 'STATE'])
            >>> fig = create_states_figs(table)
    """
    palette = cycle(Category20[20])
    resources = results.RESOURCE.unique()
    graphs = list()
    for r in resources:
        subset = results[results['RESOURCE'] == r]
        s_fig = figure(plot_width=1000, plot_height=200, tools=['xpan', 'xwheel_zoom'], active_scroll='xwheel_zoom',
                       y_range=list(reversed(subset.STATE.unique())), title='Time')
        s_fig.yaxis.axis_label = 'State'
        s_fig.step(x=subset['TIME'].values, y=subset['STATE'].values, mode='after', legend_label='res {}'.format(r),
                   color=next(palette))
        s_fig = add_two_interactive_lines(s_fig)
        graphs.append([s_fig])
    return graphs


def create_step_figs(results, time_column, resource_column, value_column):
    """
    Creates step figures from results

    :param results: DataFrame with timestamps results
    :param time_column: X-axis declaring time
    :param resource_column: resource columns defines on which to build graph
    :param value_column: Y-axis declaring possible value
    :return:

    Example::

            >>> table = DataFrame(columns=['time_column', 'resource_title', 'value_column'])
            >>> fig = create_step_figs(table, 'time_column', 'resource_title', 'value_column')
    """
    palette = cycle(Category20[20])
    resources = results[resource_column].unique()
    results[value_column] = results[value_column].apply(str)
    graphs = list()
    for r in resources:
        subset = results[results[resource_column] == r]
        s_fig = figure(plot_width=1000, plot_height=200, tools=['xpan', 'xwheel_zoom'], active_scroll='xwheel_zoom',
                       y_range=list(reversed(subset[value_column].unique())), title=time_column)
        s_fig.yaxis.axis_label = value_column
        s_fig.step(x=subset[time_column].values, y=subset[value_column].values, mode='after',
                   legend_label='res {}'.format(r), color=next(palette))
        s_fig = add_two_interactive_lines(s_fig)
        graphs.append([s_fig])
    return graphs


def create_task_analysis_fig(results):
    """
    Creates bokeh figure for task runtime results

    :param results: Dataframe of task runtime
    :return: Bokeh Figure

    Example::

            >>> table = DataFrame(columns=['TIME', 'RESOURCE', ...])
            >>> fig = create_task_analysis_fig(table)
    """
    from pnets.plotting import interval_graph
    from bokeh.plotting import figure

    if results.empty:
        return figure()
    ys = results.RESOURCE.unique()
    fig = figure(title='Time:', plot_width=1000, plot_height=800, tools=['xpan', 'xwheel_zoom'],
                 active_scroll='xwheel_zoom', y_range=ys)

    interval_graph(fig, results)
    fig = add_two_interactive_lines(fig)
    return fig
