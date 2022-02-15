from abc import ABC, abstractmethod
import operator
import numpy

from typing import Union


def format(d):
    """
    Default numeric format

    :param d: number to format
    :return: string with 4 digit precision
    """
    if numpy.isnan(d):
        return ''
    return '{:.4f)'.format(d)


def comparison(comparator, a, b):
    compare = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '=': operator.eq
    }
    return compare[comparator](a, b)


def highlight_row(d, index, threshold, comparator, color='red'):
    """
    This function highlights all the elements of the row of a Table or Pandas frame whose element d[index] is greater
    or lesser than the given threshold with the specified color

    :param d: Pandas Dataframe fed row wise
    :param index: Column Index of the value to be checked against the threshold
    :param threshold: Threshold against which the element d[index] in a row needs to be compared with
    :param comparator: Supported comparisons  >,<,==,>=,<=
    :param color: Color used to highlight the row, default color is 'red':Ex: 'yellow'
    :return: List of TextStyle object with the same number of elements it was provided with
    """

    if index not in d:
        return [None] * len(d)

    if comparison(comparator, d[index], threshold):
        styles = [TextStyle(background=color, foreground='white')] * len(d)
    else:
        styles = [None] * len(d)
    return styles


def highlight_column(d, index, color='yellow'):
    """
    This function highlights all the elements of the column of a Table or Pandas frame with the specified color

    :param d: Pandas Dataframe
    :param index: Column Index of the column to be highlighted
    :param color: Color used to highlight the row, default color is 'red':Ex: 'yellow'
    :return: List of TextStyle object with the same number of elements it was provided with
    """
    if index == d.name:
        return [TextStyle(background=color, foreground='black')] * len(d)
    else:
        return [None] * len(d)


def highlight_cells(d, threshold, comparator, color='red'):
    """
    This function highlights all the cells in a given Table or Pandas dataframe with values greater or lesser than
    threshold

    :param d: Pandas Dataframe
    :param threshold: Column Index of the column to be highlighted
    :param comparator: Supported comparisons  >,<,==,>=,<=
    :param color: Color used to highlight the row, default color is 'red':Ex: 'yellow'
    :return: List of TextStyle object with the same number of elements it was provided with
    """

    styles = numpy.array([None, TextStyle(background=color, foreground='black')])
    index = [0 if numpy.isnan(v) or not (comparison(comparator, v, threshold)) else 1 for v in d]
    return styles[index]


class SizeHint:
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'
    WIDE = 'wide'
    LARGE_WIDE = 'large wide'  # page-wide and quarter page high
    SUPER_WIDE = 'super wide'  # narrow and very wide
    HUGE = 'huge'  # page-wide and half page high


class Content:
    """
    Base class for report content.
    All content types have "tag" property that can be used to create references between the different content.

    Example:

        >>> sec1 = Section("Section #1", Table(...))
        >>> sec2 = Section("Section #2", Table(data, row_style=TextStyle(link=sec1.tag))  # all text will appear as hyperlink to section #1
        >>> report = Report("My Report", sec1, sec2)
    """

    def __init__(self):
        self._tag = '_tag_{}'.format(id(self))

    @property
    def tag(self):
        """
        Reference ID for specifying links
        """
        return self._tag

    @tag.setter
    def tag(self, val):
        self._tag = val


class ContentGroup(Content):
    """
    Content item with controlled item layout. Provides side-by-side rendering layout.

    :param align: one of top/bottom/center (default: center) - vertical content alignment.

    Example::

        >>> ContentGroup(Table(..), PieChart(...))  # render table with chart side-by-side
    """

    def __init__(self, *content, align='center'):
        super().__init__()
        self.content = list(content)
        assert align in ('center', 'top', 'bottom')
        self.align = align


class Text(Content):
    """
    Supports plain text.
    TODO: need to add support for rich text.
    """

    def __init__(self, text=None):
        super().__init__()
        self.text = text


class Title(Content):
    """
    Represents a report title
    """

    def __init__(self, text=None):
        super().__init__()
        self.text = text


class TextStyle:
    """
    Test style specification that can be applied to a table rows/columns.

    :param font: font specification in CSS format
    :param background: background color specification in #RRGGBB or named color recognized by CSS
    :param foreground: foreground color specification in #RRGGBB or named color recognized by CSS
    :param link: specifies external / document internal link. External link example:  http://some.domain.com
                 For internal links should be equal to "tag" attribute of some other element of the report.

    Example::

        >>> sec1 = Section("Details", ...)
        >>> ...
        >>> def my_row_style(row):
        >>>    # highlight row and link to sec1
        >>>    return [TextStyle(background='red', foreground='black', link=sec1.tag)] * len(row)
    """

    def __init__(self, font=None, background=None, foreground=None, link=None):
        self.font = font
        self.background = background
        self.foreground = foreground
        self.link = link


class Table(Content):
    """
    Renders a table.
    Table data is provided as pandas.DataFrame() object.

    :param data: DataFrame like the example below
    :param has_total_row: if True add freezable total row that sums all numeric columns
    :param has_column_header: if False remove horizontal header from Table
    :param has_row_header: (default: False) set to True if row header should be displayed (such as the case with MultiIndex rows)
    :param row_style: a callback that will be called with each row and should return a list of TextStyle() objects or Nones
    :param column_style: a callback that will be called with each column and should return a list of TextStyle() objects or Nones
    :param title: add title for Table
    :param format: uniform format specification for floating point values, default is str(value). Example: "{:.3f}"
                   can also specify a dictionary keyed by column names. Example: {'A': "{:.3f}", 'B': "{:.1f}%"}

    Example::

        >>> Table(pandas.DataFrame(data=[[1, 2, 3], [4, 5, 6]], columns=['A', 'B', 'C']))

    """

    def __init__(self, data=None, has_tatal_row=False, has_column_header=True, has_row_header=False,
                 title=None, format=None, row_style=None, column_style=None):
        super().__init__()
        self.data = data
        self.has_tatal_row = has_tatal_row
        self.has_column_header = has_column_header
        self.has_row_header = has_row_header
        self.title = title
        self.format = format
        self.row_style = row_style
        self.column_style = column_style


class Section(Content):
    """
    Represents a sub-section of the report. Can be nested to create hierarchical TOC.

    :param title: section title
    :param content: list of section's content objects. May contain nested Section objects.

    Example::

        >>> Report(Section("Header #1", Section("Header #2", Table(...))), ...)

    """

    def __init__(self, title, *content):
        super().__init__()
        self.title = title
        self.content = list(content)
        self.level = 0

    @property
    def sections(self):
        return [s for s in self.content if isinstance(s, Section)]

    def append(self, *content):
        """
        Append specified content items to the section. Same as section.content += (item1, item2, ...).

        :param content: Content-derived items
        :return: self

        Example::
            >>> section = Section("ABC")
            >>> section.append(Table(...), PieChart(...))
        """
        self.content += content
        return self


class Chart(Content):
    """
    Base class for presenting charts in reports.
    """

    def __init__(self, title='', *series, ytitle=None, sizehint=SizeHint.MEDIUM, title_size=None, hide_xaxis=False, hide_yaxis=False,
                 title_location=None, title_align=None):
        super().__init__()
        self.title = title
        self.series = list(series)
        self.ytitle = ytitle
        self.sizehint = sizehint
        self.title_size = title_size
        self.title_location = title_location
        self.title_align = title_align
        self.hide_xaxis = hide_xaxis
        self.hide_yaxis = hide_yaxis


class DataSeries:
    """
    Base class for data series that can be rendered in a chart.

    :param title: data series name
    :param x: x values for the series
    :param y: y values for the series
    :param alpha: the alpha factor of the series color
    :param color: optional color to be used for the data series or individual points (default: None)
                  color spec should satisfy CSS color specification ("#RRGGBB" or one of CSS named colors)

    Example::

        >>> PieChart("Dist", DataSeries("Distribution", x=["Male", "Female"], y=[1200, 1300], alpha=0.2))

    """

    def __init__(self, title='', x=None, y=None, alpha=1, color=None):
        self.title = title
        self.x = x
        self.y = y
        self.alpha = alpha
        self.color = color


class ScatterDataSeries(DataSeries):
    """
    Scatter chart data series for ScatterChart rendering. Represents a x,y simple line or step-line.

    :param title: data series name
    :param x: x values for the series
    :param y: y values for the series
    :param alpha: the alpha factor of the series color
    :param step: If true then display the data series as step function

    Example::
        >>> # render a step function:
        >>> ScatterChart("Dist", ScatterDataSeries("Distribution", x=[1, 2], y=[1200, 1300], alpha=0.2, step=True))

    """

    def __init__(self, title='', x=None, y=None, alpha=1, step=False, color=None):
        super().__init__(title=title, x=x, y=y, alpha=alpha, color=color)
        self.step = step


class IntervalDataSeries(DataSeries):
    """
    Base class for interval data series that can be rendered in a chart.

    :param title: data series name
    :param x: begin of the interval.
    :param y: lane. should be discrete value in order to change the ticks of y axis. Can be multi-level (see usage example).
    :param width: duration of the interval.
    :param color: series display color.
    :param data: a list of dictionaries where the one at index i is an additional attributes of interval i
    :param tooltip_fields: the fileds of each interval that will be displayed in the tooltip
    :param hatch_pattern: the quads hatch pattern.
    :param hatch_scale: a rough measure of the “size” of a pattern. This value has different specific meanings, depending on the pattern
    :param hatch_weight: line stroke width in units of pixels

    Example::


Name: RTL
cat: 1
value: 15000
Trace name: xxxxx


        >>> IntervalDataSeries(x=[…], y=[0, 1, 2, 3, 1, 0], width=[...], title=”process.exe”)
        >>> IntervalDataSeries(x=[1, 2,3,4,5,…15], y=[0, 1], width=[...], title=”process.exe”,
        >>>                    data=[{'Trace':xxxxxx1}, {'trace': 'name2'} 'B': 5}], tooltip_fields=['Trace'])
        >>> IntervalDataSeries(x=[...], y=['CPU0', 'CPU1', 'CPU2'], width=[...], title="process.exe")
        >>> IntervalDataSeries(x=[...], y=[('CPU','c1'), ('CPU', 'c2'), ('GPU', 'g3')], width=[...], title="process.exe")
    """

    def __init__(self, title='', x=None, y=None, width=None, color=None, data=None, tooltip_fields=None, alpha=1,
                 hatch_pattern=' ', hatch_scale=10, hatch_weight=0.5):
        super().__init__(title, x, y, alpha=alpha)
        self.width = width
        self.color = color
        self.data = data
        self.tooltip_fields = tooltip_fields
        self.hatch_pattern = hatch_pattern
        self.hatch_scale = hatch_scale
        self.hatch_weight = hatch_weight


class QuadDataSeries:
    """
    Base class for quad data series that can be rendered in a chart.

    :param title: data series name
    :param left: quad left index.
    :param right: quad right index
    :param top: quad top index
    :param bottom: quad bottom index
    :param color: series display color.
    :param data: a list of dictionaries where the one at index i is an additional attributes of quad i
    :param tooltip_fields: the fileds of each interval that will be displayed in the tooltip
    :param alpha: the alpha factor of the series color

    Example::

        >>> QuadDataSeries(left=[…], right=[0, 1, 2, 3, 1, 0], top=[...], bottom=[...], title=”process.exe”,
        >>>                data=[{'A': 1, 'B': 2}, {'A': 4, 'B': 5}, ...], tooltip_fields=['A', 'B'])
    """

    def __init__(self, title, left, right, top, bottom, color=None, data=None, tooltip_fields=None, alpha=1):
        self.title = title
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.color = color
        self.data = data
        self.tooltip_fields = tooltip_fields
        self.alpha = alpha


class PieChart(Chart):
    """
    Renders a pie chart in the report.
    Series must be a single DataSeries object with .x set to list of categories
    and .y set to non-negative measure values.
    sizehint = 'small', 'medium', 'large'. default: 'medium'
    legend_position = 'right', left. default: 'right'

    Example::

        >>> PieChart("Dist", DataSeries("Distribution", x=["Male", "Female"], y=[1200, 1300]))

    """

    def __init__(self, title, *series, sizehint=SizeHint.MEDIUM, legend_position='right'):
        super().__init__(title, *series, sizehint=sizehint)
        self.legend_position = legend_position
        if len(series) > 1:
            raise (Exception('Only a single data series object is expected for a PieChart'))


class BarChart(Chart):
    """
    Renders a regular/stacked bar chart. Each series must have same X axis labels.

    Example::

        >>> BarChart("My Chart", DataSeries(x=["a", "b", "c"], y=[10, 20, 30]))

    :param sizehint: one of 'small', 'medium', 'large'. default: 'medium'
    :param legend_position: one of 'right', left. default: 'right'
    """

    def __init__(self, title, *series, stacked=False, ytitle=None, sizehint=SizeHint.MEDIUM, legend_position='right'):
        super().__init__(title, *series, ytitle=ytitle, sizehint=sizehint, hide_x_axis=False)
        self.stacked = stacked
        self.legend_position = legend_position


class ScatterChart(Chart):
    """
    Renders a scatter chart (X/Y).
    Series must have numeric X & Y values.

    Example::

        >>> # rendering step chart:
        >>> ScatterChart("Dist", ScatterDataSeries("Distribution", x=[1, 2], y=[1200, 1300], alpha=0.2, step=True))

        >>> # rendering regular line:
        >>> ScatterChart("My Chart", ScatterDataSeries("Power", x=[1, 2], y=[1.5, 1.7]))

    :param lines: (optional) Draw lines. Default: True
    :param markers: (optional) Draw markers. Default: True
    :param sizehint: One of 'small', 'medium', 'large', or tuple of (width, height). Default: 'medium'
    :param legend_position: (optional) One of 'right', 'left'. Default: 'right'
    """

    def __init__(self, title, *series, lines=True, markers=True, xtitle=None, sizehint=SizeHint.MEDIUM, legend_position='right', title_size=None):
        super().__init__(title, *series, sizehint=sizehint, title_size=title_size)
        self.lines = lines
        self.markers = markers
        self.xtitle = xtitle
        self.legend_position = legend_position


class IntervalChart(Chart):
    """
    Renders an interval chart in the report.

    :param title: chart name
    :param series: IntervalDataSeries object
    :param sizehint: 'small', 'medium', 'large'. default: 'medium'
    :param y_axis_ticks: define custom ticks for y axis (optional), if defined - y values of IntervalDataSeries must be in y_axis_ticks
    :param title_size: the title font size. Like: '10pt', '14pt', ...
    :param hide_xaxis: If True then x axis will be hidden
    :param hide_yaxis: If True then y axis will be hidden

    Example::

        >>> IntervalChart(“CPU Processes”, IntervalDataSeries(x=[…], y=[0, 1, 2, 3, 1, 0], width=[...], title=”process.exe”)

    """

    def __init__(self, title, *series, sizehint=SizeHint.MEDIUM, y_axis_ticks=None, title_size=None, hide_xaxis=False,
                 hide_yaxis=False):
        super().__init__(title, *series, sizehint=sizehint, title_size=title_size)
        self.y_axis_ticks = y_axis_ticks


class QuadChart(Chart):
    """
    Renders an quad chart in the report.

    :param title: chart name
    :param series: QuadDataSeries object
    :param sizehint: 'small', 'medium', 'large'. default: 'medium'

    Example::

        >>> IntervalChart(“CPU Processes”, QuadDataSeries(left=[…], right=[0, 1, 2, 3, 1, 0], top=[...], bottom=[...], title=”process.exe”))

    """

    def __init__(self, title, *series, sizehint=SizeHint.MEDIUM):
        super().__init__(title, *series, sizehint=sizehint)


class ChartGroup(Content):
    """
    Content item that contains a list of charts. When the report is rendered all the charts will appear in one figure object with sync
    in x axis. A chart can be a scatter chart or interval chart

    Example::

        >>> ChartGroup(ScatterChart(..), IntervalChart(...))
    """

    def __init__(self, *charts: Union[ScatterChart, IntervalChart]):
        super().__init__()
        self.charts = list(charts)


class Report:
    """
    Represents a single report.
    Content is usually a list of sections. TOC is automatically generated from the list of sections.

    :param title: report title
    :param contents: list of content objects for the report. Usually Section() but can be any other content type.

    Example::

        >>> rep = Report("My Report", Section("Sub-section #1", Table(data=mydata)), Section(...), ...)

    """

    def __init__(self, title, *content):
        self.title = title
        self.content = list(content)

    @property
    def sections(self):
        return [s for s in self.content if isinstance(s, Section)]

    def append(self, *content):
        """
        Append specified content items to the report

        :param content: Content items

        Example::
            >>> report = Report("My Report")
            >>> report.append(Section("ABC"), Section("DEF"), ...)
        """
        self.content += content
        return self

    def update_section_levels(self):
        """
        Automatically update section levels.
        Should be called by rendering engine prior to rendering.
        """
        todo = [(self.content, 0, "sec")]
        while len(todo):
            content, level, parent_tag = todo.pop()
            for idx, c in enumerate(content):
                if isinstance(c, Section):
                    c.level = level + 1
                    # c.tag = parent_tag + '_' + str(idx)
                    todo.append((c.content, c.level, c.tag))

    def items_iter(self, hierarchy=False):
        """
        Generator method that returns an iterator over all items in the report (recursively).
        hierarchy: if true, provide tuples (item, [parent-sections]) otherwise only item is provided.
        """
        todo = [(c, []) for c in self.content]
        while len(todo):
            item, sections = todo.pop(0)

            if hierarchy:
                yield (item, sections)
            else:
                yield item

            if isinstance(item, Section):
                todo += [(c, sections + [item]) for c in item.content]


class IRenderEngine(ABC):
    """
    Abstract class for report backend renderers.
    Specific backends, such as HTML/PDF should inherit this interface.
    """

    @abstractmethod
    def render(self, report: Report):
        raise (NotImplementedError())
