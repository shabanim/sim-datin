import io
import os

from .report import IRenderEngine, Report, Table


class CSVEngine(IRenderEngine):
    """
    A back-end to publish reports tables to CSV files
    """

    @staticmethod
    def collect_tables(report, files):
        """
        Collect tables as CSV files for the record
        """
        tables = [t for t in report.items_iter(hierarchy=True) if isinstance(t[0], Table)]
        for table, hierarchy in tables:
            # write table as CSV:
            stream = io.StringIO()
            table.data.to_csv(stream, index=False)
            stream.seek(0)

            # compose table name
            title = '/'.join(s.title for s in hierarchy)
            if table.title:
                if title:
                    title += '/'
                title += table.title
            title = title.replace('.', '_')
            if title in files:
                for i in range(100000):
                    if title + '_' + str(i) not in files:
                        title = title + '_' + str(i)
                        break
            files[title] = (title + '.csv', stream)

    def __init__(self, directory_path=None):
        """
        Rendering backend to publish a report tables to a set of CSV files. The result will be rendered
        to the given directory

        :param directory_path: the output directory path
        """
        self._dir_path = directory_path

    def set_dir_path(self, dir_path):
        self._dir_path = dir_path

    def render(self, report: Report):
        """
        Override abstract IRenderBackend.render() to convert the tables to csv files

        :param report: render Report object
        """

        self.export_tables_to_csv(report)

    def export_tables_to_csv(self, report, table_names=None):
        """
        Export tables from report to csv files (Files will be saved on CSV engine directory path).
        :param report: the report object
        :param table_names: Table names to export (Export all tables if None)
        """
        files = self.render_to_json(report)
        for file_name, stream in files.items():
            if table_names is not None and file_name not in table_names:
                continue
            file_name = file_name.replace('/', '_')
            stream[1].seek(0)
            full_file_name = os.path.join(self._dir_path, file_name + '.csv')
            with open(full_file_name, 'w') as csv_file:
                csv_file.write(stream[1].getvalue().replace('\r\n', '\n'))

        return

    def render_to_json(self, report: Report):
        """
        create a d map from file title to a pair of file name and stream. Where each item in the map
        represents a table from the report. The table title is its its title concatenated with the sections
        hierarchy

        :param report: report object
        :return: JSON with report files.
        """
        files = {}
        # add tables to the record
        self.collect_tables(report, files)

        return files
