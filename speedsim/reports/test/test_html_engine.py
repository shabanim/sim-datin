import io
import os
import pandas
from unittest import TestCase


from reports import Report, Table, TextStyle, HtmlEngine, Section
from reports.test.utils import html_compare


PACKAGE_DIR = os.path.dirname(__file__)


class TestHtmlEngine(TestCase):
    def test_table_links(self):
        """
        Test generating HTML table with links
        """
        df = pandas.DataFrame([[1, 2, 3], [4, 5, 6]], columns=['a', 'b', 'c'])

        def cstyle(s):
            if s.name == 'b':
                return [TextStyle(link="https://www.cnn.com", background='yellow')] * len(s)
            else:
                return [None] * len(s)

        report = Report("Test", Table(df, format="testme {:.2f}", column_style=cstyle))
        with io.StringIO() as stream:
            eng = HtmlEngine(stream)
            eng.render(report)
            output = stream.getvalue()

        # uncomment to update expected
        if False:
            with open(os.path.join(PACKAGE_DIR, 'expected', 'test_table_links.html'), 'w') as stream:
                stream.write(output)

        with open(os.path.join(PACKAGE_DIR, 'expected', 'test_table_links.html')) as stream:
            expected = stream.read()

        self.assertTrue(html_compare(output, expected))

    def test_relative_links(self):
        """
        Test generating HTML table with links
        """
        df = pandas.DataFrame([[1, 2, 3], [4, 5, 6]], columns=['a', 'b', 'c'])

        sec1 = Section("Target #1", Table(data=df, title="Target #2"))

        def cstyle(s):
            if s.name == 'b':
                return [TextStyle(link=sec1.tag, background='yellow')] * len(s)
            else:
                return [None] * len(s)

        report = Report("Test", Table(df, format="testme {:.2f}", column_style=cstyle), sec1)
        with io.StringIO() as stream:
            eng = HtmlEngine(stream)
            eng.render(report)
            output = stream.getvalue()

        # check that there are links with references to
        self.assertTrue('<h1 id="{}">'.format(sec1.tag) in output)
        self.assertTrue('<a href="#{}">testme 2.00</a>'.format(sec1.tag) in output)
