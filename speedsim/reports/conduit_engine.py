import io
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL
import urllib

from .report import IRenderEngine, Report
from .html_engine import HtmlEngine
from .csv_engine import CSVEngine

# disable SSL certificate warnings:
requests.packages.urllib3.disable_warnings()


class ConduitEngine(IRenderEngine):
    """
    A back-end to publish reports to Conduit
    """

    def __init__(self, server_url=None, collection="reports", attributes=None,
                 template="report.html", template_paths=None):
        """
        Rendering backend to publish a report as a record in Conduit server.
        All record attributes are specified in constructor.

        :param server_url: Conduit server URL
        :param collection: Conduit server collection
        :param attributes: record attributes
        :param template: top HTML template to use (default: report.html)
        :param template_paths: Jinja2 template paths
        """
        self._server_url = server_url
        self._collection = collection
        self._attributes = attributes
        self._template = template
        self._template_paths = template_paths

    def render(self, report: Report):
        """
        Override abstract IRenderBackend.render() to post a record to Conduit

        :param report: render Report object to a conduit record
        """
        files = self.render_to_json(report)

        # prepare record:
        return self.create_record(attributes=self._attributes, files=files)

    def render_to_json(self, report: Report):
        """
        Render HTML report but do not post it to the Conduit server.

        :param report: report object
        :return: JSON with report files.
        """
        files = {}

        # render HTML report
        html_file = io.StringIO()
        html_backend = HtmlEngine(template=self._template, template_paths=self._template_paths, output_file=html_file)
        html_backend.render(report)
        html_file.seek(0)
        files['report'] = ('report.html', html_file)

        # add tables to the record
        CSVEngine.collect_tables(report, files)

        return files

    def create_record(self, files=None, attributes=None):
        """
        Create a record in Conduit

        :param files: a dict of file_name -> stream
        :param attributes: additional record attributes
        """
        url = urllib.parse.urljoin(self._server_url, 'tools/' + self._collection + '/records')
        auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        proxies = {"http": None, "https": None}
        res = requests.post(url, auth=auth, verify=False, files=files, data=attributes, proxies=proxies)
        if res.status_code != 201:  # HTTP_CREATED
            raise (Exception(res.text))
        return res.json()
