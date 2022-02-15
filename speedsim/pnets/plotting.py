"""
Collection of utilities for plotting simulation results with bokeh
"""
from itertools import cycle

import pandas
from bokeh.models import (CategoricalAxis, ColumnDataSource, DataTable,
                          NumberFormatter, TableColumn)
from bokeh.palettes import Category20
from bokeh.plotting.helpers import _get_range, _get_scale
from bokeh.transform import dodge

from pnets import attributes


def interval_graph(fig, results, colors=None):
    """
    Display lanes with resources and tasks executing on them
    :param fig: bokeh figure
    :param results: simulation results
    :param colors: if specified, provides a map of transition name to color
    """
    from bokeh.models import HoverTool
    if colors is None:
        colors = {}
    palette = cycle(Category20[20])

    resources = sorted(set(results[['RESOURCE', 'RESOURCE_IDX']].itertuples(index=False)))
    ticks = ["{}.{}".format(r, i) for r, i in resources]
    fig.y_range = _get_range(ticks)
    fig.y_scale = _get_scale(fig.y_range, 'auto')
    if len(fig.left) and not isinstance(fig.left[0], CategoricalAxis):
        fig.left[0] = CategoricalAxis()

    # figure.x_range = resources
    rectangles = []

    for start, finish, name, resource, resource_idx, duration in results[['START', 'FINISH', 'TRANSITION', 'RESOURCE',
                                                                          'RESOURCE_IDX',
                                                                          'DURATION']].itertuples(index=False):
        if name in colors:
            color = colors[name]
        else:
            color = next(palette)
            colors[name] = color

        rectangles.append((start, finish, '{}.{}'.format(resource, resource_idx), color, name, duration))

    rectangles = pandas.DataFrame(rectangles, columns=['left', 'right', 'lane', 'color', 'NAME', 'duration'])
    src = ColumnDataSource.from_df(rectangles)
    quad = fig.quad(source=src, left='left', right='right', bottom=dodge('lane', -0.45, range=fig.y_range),
                    top=dodge('lane', +0.45, range=fig.y_range), color='color')
    hover = HoverTool(renderers=[quad], tooltips=[('name', '@NAME'), ('start', '@left'), ('finish', '@right'),
                                                  ('duration', '@duration')])
    fig.add_tools(hover)


def flame_graph(fig, results, colors=None):
    """
    Render flame graph for specified simulation results.
    :param fig: Bokeh figure
    :param results: pandas.DataFrame() with START, FINISH and NAME columns
                    NAME column will be available to figure data source and can be displayed in a tooltip
                    by specifying tooltips=[('name', '@NAME')] to figure() constructor.
    :param colors: (optional) dictionary to map task name to a color
    """
    if colors is None:
        colors = {}
    palette = cycle(Category20[20])

    rectangles = []

    lanes = {}  # for each lane, last busy timestamp
    for start, finish, name in results[['START', 'FINISH', 'NAME']].sort_values('START').itertuples(index=False):
        # find an existing lane:
        next_lane = None
        for lane, ts in lanes.items():
            if ts <= start:
                next_lane = lane
                break

        if next_lane is None:
            next_lane = len(lanes)

        if name in colors:
            color = colors[name]
        else:
            color = next(palette)
            colors[name] = color

        lanes[next_lane] = finish
        rectangles.append((start, finish, next_lane, color, name))

    rectangles = pandas.DataFrame(rectangles, columns=['left', 'right', 'bottom', 'color', 'NAME'])
    rectangles['top'] = rectangles['bottom'] + 1.0
    src = ColumnDataSource.from_df(rectangles)
    fig.quad(source=src, left='left', right='right', bottom='bottom', top='top', color='color')


def task_runtime_table(pn_model, sim_results, width=1200):
    """
    Returns Bokeh DataTable with comparison of original vs actual runtime for tasks.
    :param pn_model: PnmlModel that was simulated (for extracting original runtime)
    :param sim_results: simulation results with DURATION, TRANSACTION and NAME columns
    :return: Bokeh.DataTable with the runtime comparison data
    """
    df = sim_results[['NAME', 'TRANSITION', 'DURATION']]

    orig_df = pandas.DataFrame([
        (tran.id, tran.get_attribute(attributes.RUNTIME)) for net in pn_model.nets for tran in net.transitions
    ], columns=['TRANSITION', 'ORIG_DURATION'])

    df = pandas.merge(df, orig_df, on='TRANSITION', how='left')
    df['DIFF_VAL'] = df['DURATION'] - df['ORIG_DURATION']
    df['DIFF_PERC'] = 100 * ((df['DURATION'] - df['ORIG_DURATION']) / df['ORIG_DURATION']).fillna(0)

    default_formatter = NumberFormatter(format='0.00')

    return DataTable(source=ColumnDataSource(df),
                     columns=[
                         TableColumn(title='ID', field='TRANSITION'),
                         TableColumn(title='NAME', field='NAME'),
                         TableColumn(title='DURATION', field='DURATION', formatter=default_formatter),
                         TableColumn(title='ORIG. DURATION', field='ORIG_DURATION', formatter=default_formatter),
                         TableColumn(title='DIFF (usec)', field='DIFF_VAL', formatter=default_formatter),
                         TableColumn(title='DIFF (%)', field='DIFF_PERC', formatter=default_formatter)
                     ], width=width)
