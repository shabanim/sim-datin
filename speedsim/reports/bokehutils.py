"""
This module contains utilities that compliment missing features in
"""
from bokeh.models import FactorRange, CategoricalAxis, ColumnDataSource, CrosshairTool, CustomJS
try:
    # v2.0
    from bokeh.plotting._plot import get_scale
except:  # noqa
    # v1.4
    from bokeh.plotting.helpers import _get_scale as get_scale
from bokeh.transform import dodge


def bars(fig, x, y, source=None, num_total=1, this_index=0, **kwargs):
    """
    Plots bokeh histogram in specified figure.

    :param x: X axis values / column name (will be converted to strings for categorical X axis)
    :param y: Y axis values / column name (floats)
    :param source: ColumnDataSource (optional)
    :param num_total: total number of series that will be displayed. Default: 1
    :param this_index: index of this series. Default: 0
    :param kwargs: other arguments are the same as bokeh.plotting.Figure.vbar() arguments such as alpha, color, ...
    """
    if source is None:
        source = ColumnDataSource({
            'x': list(map(str, x)),
            'y': y
        })
        x = 'x'
        y = 'y'

    # update figure X axis if it isn't discrete
    if not isinstance(fig.x_range, FactorRange):
        fig.x_range = FactorRange(factors=source.data[x])
        fig.x_scale = get_scale(fig.x_range, 'auto')
        if len(fig.below) and not isinstance(fig.below[0], CategoricalAxis):
            fig.below[0] = CategoricalAxis()

    bar_width = 0.8/num_total  # bar width with spacing

    return fig.vbar(x=dodge(x, -0.4 + (this_index + 0.5) * bar_width, range=fig.x_range),
                    top=y, source=source, width=bar_width, **kwargs)


def to_rgb(color: str):
    """
    Convert CSS-style colors to RGB. Requires 'webcolors' package

    :param color:
    :return: tuple (r, g, b)
    """
    import webcolors
    if color[0] == '#':
        return webcolors.hex_to_rgb(color)
    else:
        return webcolors.name_to_rgb(color)


def darker(color: str, factor=0.7) -> str:
    """
    Returns same color 50% darker (in RGB)
    :param color: color in CSS format
    :param factor: (0.0-1.0) factor to multiply by
    :return: #RRGGBB
    """
    rgb = to_rgb(color)

    return "#{:02x}{:02x}{:02x}".format(int(rgb[0] * factor), int(rgb[1] * factor), int(rgb[2] * factor))


def add_crosshair(*figures):
    """
    Add aligned vertical crosshair between specified figures

    :param figures: figures to link
    """
    js_move = '''
            if(cb_obj.x >= fig.x_range.start && cb_obj.x <= fig.x_range.end &&
               cb_obj.y >= fig.y_range.start && cb_obj.y <= fig.y_range.end)
            {
                cross_list.forEach(cross => cross.spans.height.computed_location = cb_obj.sx)
            }
            else
            {
                cross_list.forEach(cross => cross.spans.height.computed_location = null)
            }
        '''
    js_leave = 'cross_list.forEach(cross => cross.spans.height.computed_location = null)'

    tools = [CrosshairTool(line_color='#202020', line_alpha=0.5) for fig in figures]

    for tool, fig in zip(tools, figures):
        fig.add_tools(tool)
        args = {'cross_list': [t for t in tools if t is not tool], 'fig': fig}
        fig.js_on_event('mousemove', CustomJS(args=args, code=js_move))
        fig.js_on_event('mouseleave', CustomJS(args=args, code=js_leave))
