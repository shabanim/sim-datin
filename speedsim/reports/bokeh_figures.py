import bokeh
import html
import pandas
import itertools
import numpy

from math import pi
from bokeh.models import LabelSet, ColumnDataSource, Legend, LegendItem, BoxAnnotation, FactorRange
from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.palettes import Category20_20 as palette
from .report import BarChart, ScatterChart, IntervalChart, PieChart, QuadChart, SizeHint
from .bokehutils import darker


CHART_SIZE = {
    SizeHint.SMALL: (250, 250),
    SizeHint.MEDIUM: (500, 500),
    SizeHint.LARGE: (900, 900),
    SizeHint.WIDE: (900, 300),
    SizeHint.SUPER_WIDE: (1200, 300),
    SizeHint.LARGE_WIDE: (1200, 600),
    SizeHint.HUGE: (1600, 600)
}

FONT_SIZE = {
    SizeHint.SMALL: '7pt',
    SizeHint.MEDIUM: '10pt',
    SizeHint.LARGE: '15pt',
    SizeHint.WIDE: '10pt',
    SizeHint.SUPER_WIDE: '10pt',
    SizeHint.LARGE_WIDE: '10pt',
    SizeHint.HUGE: '10pt'
}

TITLE_SIZE = {
    SizeHint.SMALL: '10pt',
    SizeHint.MEDIUM: '20pt',
    SizeHint.LARGE: '30pt',
    SizeHint.WIDE: '20pt',
    SizeHint.SUPER_WIDE: '20pt',
    SizeHint.LARGE_WIDE: '20pt',
    SizeHint.HUGE: '20pt'
}


def render_chart(chart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    type_2_func = {
        BarChart: render_bar_chart,
        ScatterChart: render_scatter_chart,
        IntervalChart: render_interval_chart,
        PieChart: render_pie_chart,
        QuadChart: render_quad_chart
    }
    if type(chart) not in type_2_func:
        raise Exception("Could not find figure creating function for the chart type: " + str(type(chart)))

    return type_2_func[type(chart)](chart)


def render_bar_chart(chart: BarChart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    data = pandas.DataFrame({
        s.title: pandas.Series(s.y, index=[str(v) for v in s.x]) for s in chart.series
    })

    # pandas.series will sort index alphabetically when index given are categorical, this is by design
    # to get back data in unsorted way we need to reindex() on longest 'x' in given chart series
    unsorted_index = []
    unsorted_index_len = 0
    for s in chart.series:
        if len(s.x) > unsorted_index_len:
            unsorted_index_len = len(s.x)
            unsorted_index = s.x

    data = data.reindex([str(v) for v in unsorted_index])
    data.index.name = 'x'
    data = data.reset_index().fillna(0)
    source = bokeh.models.ColumnDataSource(data)

    TOOLTIPS = [
        ('Name', '$name'),
        ('Category', '@x'),
        ('Value', '@$name')
    ]

    TOOLS = ['hover']

    # labels = [s.title for s in chart.series]
    # legend_width = len(max(labels, key=len)) * 10

    sizehint = chart.sizehint
    if isinstance(sizehint, str):
        width = CHART_SIZE[sizehint][0]
        height = CHART_SIZE[sizehint][1]
    else:
        width = sizehint[0]
        height = sizehint[1]
        sizehint = SizeHint.MEDIUM

    fig = figure(title=chart.title,
                 plot_width=width,
                 plot_height=height,
                 hide_x_axis=chart.hide_x_axis,
                 x_range=list(data['x'].values),
                 tooltips=TOOLTIPS,
                 tools=TOOLS,
                 toolbar_location=None)

    fig.title.text_font_size = TITLE_SIZE[sizehint]

    colors = itertools.cycle(palette)

    GROUP_WIDTH = 0.8

    width = GROUP_WIDTH / len(chart.series)

    legend_items = []

    for idx, s in enumerate(chart.series):
        item = fig.vbar(x=dodge('x', - GROUP_WIDTH / 2 + idx * width + width / 2, range=fig.x_range),
                        name=s.title,
                        top=s.title,
                        source=source,
                        width=width * 0.9,
                        color=next(colors),
                        fill_alpha=s.alpha,
                        line_alpha=s.alpha)
        legend_items.append((s.title, [item]))

    if len(legend_items) > 1:
        legend = Legend(items=legend_items)
        legend.label_text_font_size = FONT_SIZE[sizehint]
        fig.add_layout(legend, chart.legend_position)

    return fig


def render_pie_chart(chart: PieChart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    series = chart.series[0]
    if len(series.x) == 0 or len(series.y) == 0:
        return bokeh.models.Div()

    data = pandas.DataFrame({
        'category': series.x,
        'value': series.y
    })

    RADIUS = 0.7
    data['angle'] = data['value'] / data['value'].sum() * 2 * pi
    data['start_angle'] = data['angle'].cumsum().shift(1).fillna(0)
    data['end_angle'] = data['start_angle'] + data['angle']
    colors = itertools.cycle(palette)
    data['color'] = [next(colors) for c in range(len(series.x))]
    data['percentage'] = data['value'] / data['value'].sum() * 100
    data = data[data.value > 0]
    data['percentage'] = data['percentage'].apply(lambda x: str(round(x, 1)) + '%')
    data['x'] = RADIUS * 0.66 * numpy.cos(data['start_angle'] + 0.5 * data['angle'])
    data['y'] = RADIUS * 0.66 * numpy.sin(data['start_angle'] + 0.5 * data['angle'])

    TOOLTIPS = [('Category', '@category'), ('Value', '@value'), ('Percentage', '@percentage')]

    source = ColumnDataSource(data)

    legend_width = len(max(series.x, key=len)) * 10

    sizehint = chart.sizehint
    if isinstance(sizehint, str):
        width = CHART_SIZE[sizehint][0]
        height = CHART_SIZE[sizehint][1]
    else:
        width, height = sizehint
        sizehint = SizeHint.MEDIUM

    fig = figure(title=chart.title,
                 plot_width=width + legend_width,
                 plot_height=height,
                 tools='hover', tooltips=TOOLTIPS, x_range=(-1.0, 1.0), y_range=(-1.0, 1.0),
                 toolbar_location=None)

    render = fig.wedge(x=0, y=0, radius=RADIUS, start_angle='start_angle', end_angle='end_angle',
                       line_color='white', line_width=0.2, fill_color='color', source=source)

    fig.title.text_font_size = TITLE_SIZE[sizehint]
    fig.toolbar.logo = None

    labels_data = data[data['angle'] > 0.5]
    labels_source = ColumnDataSource(labels_data)
    labels = LabelSet(x='x', y='y', text='percentage', text_font_size=FONT_SIZE[sizehint],
                      text_color='white', level='glyph', source=labels_source, render_mode='canvas',
                      text_align='center', text_baseline='middle')
    fig.add_layout(labels)

    fig.axis.axis_label = None
    fig.axis.visible = False
    fig.grid.grid_line_color = None
    fig.outline_line_color = None

    legend = Legend(items=[LegendItem(label=dict(field='category'), renderers=[render])])
    legend.label_text_font_size = FONT_SIZE[sizehint]
    fig.add_layout(legend, chart.legend_position)
    # disable legend
    if len(series.x) <= 1:
        legend.visible = False

    return fig


def render_scatter_chart(chart: ScatterChart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    TOOLTIPS = [('Category', '$name'),
                ('x', '@x'),
                ('y', '@y')]

    # labels = [s.title for s in chart.series]
    # legend_width = len(max(labels, key=len)) * 10

    sizehint = chart.sizehint
    if isinstance(sizehint, str):
        width = CHART_SIZE[sizehint][0]
        height = CHART_SIZE[sizehint][1]
    else:
        width, height = sizehint
        sizehint = SizeHint.MEDIUM

    extra = {}

    if chart.xtitle:
        extra['x_axis_label'] = chart.xtitle

    if chart.ytitle:
        extra['y_axis_label'] = chart.ytitle

    fig = bokeh.plotting.figure(
        title=chart.title,
        tooltips=TOOLTIPS,
        tools=['hover', 'xwheel_zoom', 'xpan', 'reset'],
        plot_width=width,
        plot_height=height,
        **extra
    )

    if chart.title_size is not None:
        title_size = chart.title_size
    else:
        title_size = TITLE_SIZE[sizehint]

    fig.title.text_font_size = title_size
    fig.xaxis.visible = (not chart.hide_xaxis)
    fig.yaxis.visible = (not chart.hide_yaxis)
    fig.toolbar.logo = None

    colors = itertools.cycle(palette)

    legend_items = []

    for s in chart.series:
        color = s.color if s.color is not None else next(colors)
        assert chart.lines or chart.markers
        if chart.lines:
            # line does not support sequence for colors
            line_color = color if isinstance(color, str) else next(colors)
            if hasattr(s, 'step') and s.step:
                item = fig.step(x=s.x, y=s.y, name=s.title, color=line_color, line_width=2, line_alpha=s.alpha)
            else:
                item = fig.line(x=s.x, y=s.y, name=s.title, color=line_color, line_width=2, line_alpha=s.alpha)
        if chart.markers:
            i2 = fig.circle(x=s.x, y=s.y, name=s.title, color=color, size=5, fill_alpha=s.alpha, line_alpha=s.alpha)
            if not chart.lines:
                item = i2
        legend_items.append((s.title, [item]))

    if len(legend_items) > 1:
        legend = Legend(items=legend_items)
        legend.label_text_font_size = FONT_SIZE[sizehint]
        fig.add_layout(legend, chart.legend_position)

    if chart.title_location:
        fig.title_location = chart.title_location
    if chart.title_align:
        fig.title.align = chart.title_align

    return fig


def render_interval_chart(chart: IntervalChart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    RECT_HEIGHT = 0.9
    colors = itertools.cycle(palette)
    colors_dict = {}
    BOX_COLOR = '#E0E0E0'

    TOOLS = ['xwheel_zoom', 'xpan', 'box_zoom', 'reset']

    # custom tooltip for displaying extra content per interval
    TOOLTIPS = """
        <table>
            <style>
                td.tt-title {
                    font-weight: bold;
                    color: rgb(0, 0, 128);
                    text-align: left;
                }
            </style>
            <tbody>
                <tr> <td class="tt-title">Name</td>  <td>@title</td> </tr>
                <tr> <td class="tt-title">Start</td> <td>@left{1.111111}</td> </tr>
                <tr> <td class="tt-title">End</td>   <td>@right{1.111111}</td> </tr>
                <tr> <td class="tt-title">Duration</td>   <td>@width{1.111111}</td> </tr>
                @data{safe}
            <tbody>
        </table>
    """

    def _to_tooltip(data):
        result = []
        for k, v in data.items():
            result.append('<tr>  <td class="tt-title">{}</td> <td>{}</td> </tr>'.format(html.escape(k), html.escape(str(v))))
        return '\n'.join(result)

    sizehint = chart.sizehint
    if isinstance(sizehint, str):
        width = CHART_SIZE[sizehint][0]
        height = CHART_SIZE[sizehint][1]
    else:
        width, height = sizehint
        sizehint = SizeHint.MEDIUM

    fig = bokeh.plotting.figure(
        title=chart.title,
        tools=TOOLS,
        plot_width=width,
        plot_height=height,
        tooltips=TOOLTIPS,
        y_range=FactorRange(*chart.y_axis_ticks) if chart.y_axis_ticks else None
    )

    groups_idx = []
    if chart.y_axis_ticks:
        tick_to_idx = {tick: idx for idx, tick in enumerate(chart.y_axis_ticks)}

        if all(isinstance(item, tuple) for item in chart.y_axis_ticks):
            #  if y_axis ticks is instance of list of tuples, we have multi-level axis,
            #  group y axis ticks by group name and get start and end index for each group, used later for
            #  box annotation.
            idx = 0
            for _, group in itertools.groupby(chart.y_axis_ticks, key=lambda x: x[0]):
                group_size = len(list(group))
                groups_idx.append((idx, idx + group_size))
                idx += group_size

            groups_idx.pop(0)  # first box is white
            fig.yaxis.group_label_orientation = 'horizontal'
            fig.y_range.group_padding = 0

    fig.x_range.bounds = (0, None)
    if chart.title_size is not None:
        title_size = chart.title_size
    else:
        title_size = TITLE_SIZE[sizehint]

    fig.title.text_font_size = title_size
    fig.xaxis.visible = (not chart.hide_xaxis)
    fig.yaxis.visible = (not chart.hide_yaxis)

    for s in chart.series:
        title = s.title
        if title in colors_dict:
            color, line_color = colors_dict[s.title]
        else:
            color = s.color if s.color is not None else next(colors)
            if isinstance(color, list) or isinstance(color, tuple):
                line_color = [darker(c) for c in color]
            else:
                line_color = darker(color)
            colors_dict[title] = color, line_color

        if s.data is not None:
            data_str_list = [_to_tooltip(d) for d in s.data]
        else:
            data_str_list = [''] * len(s.x)

        df = pandas.DataFrame({
            'left': s.x,
            'y': [tick_to_idx[y] + 0.5 for y in s.y] if chart.y_axis_ticks else s.y,  # +0.5 to align rectangle to be parallel to the tick
            'width': s.width,
            'title': title,
            'color': color,
            'line_color': line_color,
            'data': data_str_list
        })

        df['right'] = df['left'] + df['width']

        source = ColumnDataSource.from_df(df)
        fig.quad(left='left',
                 right='right',
                 top=dodge('y', + RECT_HEIGHT / 2),
                 bottom=dodge('y', - RECT_HEIGHT / 2),
                 fill_color='color',
                 line_color='line_color',
                 line_width=0.5,
                 name='name',
                 source=source,
                 hatch_pattern=s.hatch_pattern,
                 hatch_scale=s.hatch_scale,
                 hatch_weight=s.hatch_weight,
                 fill_alpha=s.alpha,
                 line_alpha=s.alpha)

    for bottom, top in groups_idx[::2]:
        fig.add_layout(BoxAnnotation(top=top,
                                     bottom=bottom,
                                     fill_color=BOX_COLOR,
                                     level='underlay'))

    if chart.title_location:
        fig.title_location = chart.title_location
    if chart.title_align:
        fig.title.align = chart.title_align

    return fig


def render_quad_chart(chart: QuadChart):
    """
    Create a bokeh figure object for the given chart

    :param chart: a Chart object
    :return: bokeh figure
    """
    colors = itertools.cycle(palette)
    colors_dict = {}

    TOOLS = ['xwheel_zoom', 'xpan', 'box_zoom', 'reset']

    TOOLTIPS = [
        ('Name', '@title'),
        ('Left', '@left{1.11}'),
        ('Right', '@right{1.11}'),
        ('Top', '@top{1.11}'),
        ('Bottom', '@bottom{1.11}'),
        ('Data', '@data')
    ]

    sizehint = chart.sizehint
    if isinstance(sizehint, str):
        width = CHART_SIZE[sizehint][0]
        height = CHART_SIZE[sizehint][1]
    else:
        width = sizehint[0]
        height = sizehint[1]

    fig = bokeh.plotting.figure(
        title=chart.title,
        tools=TOOLS,
        plot_width=width,
        plot_height=height,
        tooltips=TOOLTIPS
    )

    fig.x_range.bounds = (0, None)

    for s in chart.series:
        title = s.title
        if title in colors_dict:
            color = colors_dict[s.title]
        else:
            color = s.color if s.color is not None else next(colors)
            colors_dict[title] = color

        data_str_list = []
        for i in range(0, len(s.left)):
            data_str = ''
            attrs_str = []
            if s.tooltip_fields is not None:
                for attr in s.tooltip_fields:
                    if s.data is None or len(s.data) < i + 1 or attr not in s.data[i]:
                        continue
                    attrs_str.append(attr + '=' + str(s.data[i][attr]))
                data_str = ', '.join(attrs_str)
            data_str_list.append(data_str)

        df = pandas.DataFrame({
            'left': s.left,
            'right': s.right,
            'top': s.top,
            'bottom': s.bottom,
            'title': title,
            'color': color,
            'data': data_str_list
        })

        source = ColumnDataSource.from_df(df)
        fig.quad(left='left',
                 right='right',
                 top='top',
                 bottom='bottom',
                 fill_color='color',
                 line_color='black',
                 line_width=0.5,
                 name='name',
                 source=source,
                 fill_alpha=s.alpha,
                 line_alpha=s.alpha)

    return fig
