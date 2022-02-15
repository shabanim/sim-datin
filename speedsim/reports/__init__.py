"""
*reports* package offers API for abstract report definition and rendering and eases the task of generating visual output for data analysis.
A report object is defined using :py:class:`reports.Report` class with any of the supported content types (Section, Table, PieChart, ...)
It then can be rendered into HTML file using :py:func:`~reports.render_report`() or displayed inside the application with *display_report()*
"""
from .report import Report, Table, Section, ContentGroup, Text, PieChart, BarChart, DataSeries, IRenderEngine, Title,\
    ScatterChart, TextStyle, highlight_cells, highlight_column, highlight_row, format, IntervalChart, IntervalDataSeries,\
    Content, QuadDataSeries, QuadChart, ChartGroup, ScatterDataSeries, SizeHint

from .html_engine import HtmlEngine
from .conduit_engine import ConduitEngine
from .csv_engine import CSVEngine
from .utils import render_report, _pandas_template_wa

_pandas_template_wa()

__all__ = ['Report', 'Table', 'Section', 'ContentGroup', 'Text', 'Title', 'PieChart', 'BarChart', 'IntervalChart',
           'DataSeries', 'IntervalDataSeries', 'IRenderEngine', 'format', 'HtmlEngine', 'ConduitEngine', 'CSVEngine',
           'render_report', 'ScatterChart', 'TextStyle', 'highlight_column', 'highlight_cells', 'highlight_row', 'Content', 'QuadDataSeries',
           'QuadChart', 'ChartGroup', 'ScatterDataSeries', 'SizeHint']
