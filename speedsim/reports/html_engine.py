import itertools

import bokeh
import pandas
from bokeh.embed import components
from bokeh.plotting import gridplot
from jinja2 import Environment, FileSystemLoader
import numpy
import os
import sys
from .report import IRenderEngine, Report, Section, Table, PieChart, BarChart, ContentGroup, ScatterChart, Text, \
    TextStyle, IntervalChart, QuadChart, ChartGroup, SizeHint
from .bokeh_figures import render_chart

CHART_SIZE = {
    SizeHint.SMALL: (250, 250),
    SizeHint.MEDIUM: (500, 500),
    SizeHint.LARGE: (900, 900),
    SizeHint.WIDE: (900, 300),
}

FONT_SIZE = {
    SizeHint.SMALL: '7pt',
    SizeHint.MEDIUM: '10pt',
    SizeHint.LARGE: '15pt',
    SizeHint.WIDE: '10pt',
}

TITLE_SIZE = {
    SizeHint.SMALL: '10pt',
    SizeHint.MEDIUM: '20pt',
    SizeHint.LARGE: '30pt',
    SizeHint.WIDE: '20pt'
}


def get_template_path():
    """
    Get base directory for the module (code installation path).
    """
    if os.path.exists(__file__):
        return os.path.join(os.path.dirname(__file__), 'templates')  # running from source
    else:
        return os.path.join(os.path.dirname(sys.executable), 'templates')  # running from PyInstaller distribution


builtin_paths = [get_template_path()]

builtin_template_map = {
    Section: 'section.html',
    Table: 'table.html',
    ContentGroup: 'content_group.html',
    Text: 'text.html',
}


class HtmlEngine(IRenderEngine):
    """
    Rich HTML report output backend.
    Uses Bokeh to render interactive charts.
    """

    def __init__(self, output_file, template="report.html", template_paths=None):
        self._output_file = output_file
        self._template = template
        self._template_paths = template_paths if template_paths else []
        self._env = Environment(loader=FileSystemLoader(self._template_paths + builtin_paths))
        self._env.globals.update({
            'render': self.render_content,
            'render_table': self.render_table,
            'render_header': self._render_header,
        })
        self._template_cache = {}

    def render(self, report: Report):
        """
        Overrides abstract method to render the report into an HTML page.
        :param report: report.Report object to render.
        """
        template = self._env.get_template(self._template)

        report.update_section_levels()
        html_out = template.render({'data': report, 'utils': self})
        if isinstance(self._output_file, str):
            with open(self._output_file, 'w') as file:
                file.write(html_out)
        else:
            self._output_file.write(html_out)

    def _render_header(self):
        """
        Renders additional content for the HTML <head>...</head>
        :return: HTML text
        """
        return bokeh.resources.CDN.render()

    def render_content(self, item):
        """
        Called from inside HTML rendering code to render a specific content item.
        :param item: report.Content derived object
        :return: rendered HTML
        """
        t = type(item)

        # type is handled by Jinja template code:
        if t in builtin_template_map:
            if t not in self._template_cache:
                self._template_cache[t] = self._env.get_template(builtin_template_map[t])

            return self._template_cache[t].render({'data': item, 'utils': self})

        # type is handled internally
        handlers = {
            PieChart: self.render_chart,
            BarChart: self.render_chart,
            ScatterChart: self.render_chart,
            IntervalChart: self.render_chart,
            QuadChart: self.render_chart,
            ChartGroup: self.render_chart_group
        }
        return handlers[t](item)

    def render_chart_group(self, chart_group: ChartGroup):
        """
        Renders a chart group. The charts will be placed one below the other and all of them synced with the first chart x axis

        :param chart_group: a chart group option
        :return: the html of the chart group
        """
        figs = [render_chart(c) for c in chart_group.charts]
        if len(figs) > 1:
            for fig in figs[1:]:
                fig.x_range = figs[0].x_range

        plot = gridplot([[f] for f in figs])

        script, div = components(plot)
        return script + '\n' + div

    def render_chart(self, chart):
        """
        Renders Chart object using Bokeh

        :param chart: Pie chart data
        :return: HTML
        """
        fig = render_chart(chart)
        script, div = components(fig)
        return script + '\n' + div

    def render_table(self, table):
        """
        Render pandas DataFrame using pandas.Style object
        :param table: pandas.DataFrame
        :return: HTML output
        """
        df = table.data
        style = df.style

        # single format for the whole table:
        if table.format:
            style = style.format(table.format)

        # apply by-row / by-column styling:
        table_style = table.row_style or table.column_style
        if table_style is not None:

            # collect all table styles:
            text_styles = numpy.empty(df.shape, dtype=object)

            if isinstance(table_style, TextStyle):
                text_styles[:] = table_style
            else:
                # should be callable
                if not callable(table_style):
                    raise ValueError("row_style/column_style should be of type TextStyle or a callback")

                if table.row_style:
                    for row in range(df.shape[0]):
                        text_styles[row, :] = table_style(df.iloc[row])
                else:
                    for idx, col in enumerate(df.columns):
                        text_styles[:, idx] = table_style(df[col])

            has_links = False
            for r, c in itertools.product(range(text_styles.shape[0]), range(text_styles.shape[1])):
                if text_styles[r, c] is not None and text_styles[r, c].link is not None:
                    has_links = True
                    break

            if has_links:
                # need to reapply user-provided formatting explicitly:
                if isinstance(table.format, str):
                    def apply_format(row, col, val):
                        return table.format.format(val)
                elif callable(table.format):
                    def apply_format(row, col, val):
                        return table.format(val)
                elif isinstance(table.format, dict):
                    def apply_format(row, col, val):
                        cname = df.columns[col]
                        if cname not in table.format:
                            return val
                        f = table.format[cname]
                        if isinstance(f, str):
                            return f.format(val)
                        if callable(f):
                            return f(val)
                        else:
                            return val
                else:
                    if table.format is not None:
                        sys.stderr.write("-E- Unknown table format specified. Supported values are string, callable or dict of string/callable\n")

                    def apply_format(row, col, val):
                        return val

                # selectively apply link formatting:
                new_df = numpy.empty(df.shape, dtype=object)
                for row, col in itertools.product(range(text_styles.shape[0]), range(text_styles.shape[1])):
                    if text_styles[row, col] is None or text_styles[row, col].link is None:
                        new_df[row, col] = apply_format(row, col, df.iloc[row, col])
                    else:
                        new_df[row, col] = '<a href="{}">{}</a>'.format(self._normalize_link(text_styles[row, col].link),
                                                                        apply_format(row, col, df.iloc[row, col]))

                # NOTE: overriding content here with new data
                df = pandas.DataFrame(new_df, columns=df.columns)
                style = df.style

            if text_styles.shape[0]:
                css_styles = numpy.vectorize(self._textstyle_to_css)(text_styles)
            else:
                css_styles = []
            style = style.apply(lambda x: pandas.DataFrame(css_styles, columns=df.columns, index=df.index), axis=None)

        # return df.to_html(index=False, classes=("table", "table-striped", "table-bordered", "table-hover", "table-sm"), na_rep="")
        # using styles:
        # FIXME: control NA representation. Currently is not supported by Styler definition (to_html() had na_rep option)
        if not table.has_row_header:
            # FIXME: hide_index() is not released yet
            style = style.set_table_styles([
                {'selector': '.row_heading', 'props': [('display', 'none')]},
                {'selector': '.index_name', 'props': [('display', 'none')]},
                {'selector': '.blank.level1', 'props': [('display', 'none')]},
                {'selector': '.blank.level0', 'props': [('display', 'none')]}
            ])

        style = style.set_table_attributes('class="table table-striped table-bordered table-hover table-sm"')

        return style.render()

    def _textstyle_to_css(self, style):
        """
        Convert report.TextStyle definition to CSS string
        :param style: report.TextStyle definition
        :return: CSS string
        """
        if style is None:
            return ''

        result = ''
        if style.background is not None:
            result += 'background: ' + str(style.background) + ';'
        if style.foreground is not None:
            result += 'color: ' + str(style.foreground) + ';'
        if style.font is not None:
            result += 'font: ' + str(style.font) + ';'

        return result

    def _normalize_link(self, link):
        """
        Make sure relative links are in proper format
        :param link:
        :return:
        """
        if "://" not in link and not link.startswith('#'):
            return '#' + link
        return link  # absolute or already start with '#'
