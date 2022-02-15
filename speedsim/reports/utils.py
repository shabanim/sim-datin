from .html_engine import HtmlEngine


def render_report(report, html_file):
    """
    Render report to an HTML file.

    :param report: Report() object
    :param html_file: output HTML file path
    """
    report.update_section_levels()
    eng = HtmlEngine(html_file)
    eng.render(report)


def _pandas_template_wa():
    """
    Apply a WA for frozen executables.
    Pandas DataFrame style attempts to use pkg_resource to load HTML template for jinja2.
    By default, it falls back to NullProvider and fails.
    This overrides the provider to use default. Templates should be placed under <prog-path>/pandas/io/formats/templates
    """
    import sys
    if not hasattr(sys, 'frozen'):
        return

    import pkg_resources
    import pyimod03_importers

    if isinstance(pkg_resources.get_provider('pandas'), pkg_resources.NullProvider):
        pkg_resources.register_loader_type(pyimod03_importers.FrozenImporter, pkg_resources.DefaultProvider)
