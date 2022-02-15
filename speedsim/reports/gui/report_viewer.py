import os
from PyQt5 import Qt, QtWidgets

from reports import CSVEngine
from reports.html_engine import HtmlEngine

from qtutils.utils import get_icon, Wait
from qtutils import notify, slot
from qtutils.web_engine_view import WebEngineView


import tempfile


class ReportViewer(QtWidgets.QWidget):
    """
    Renders reports.Report() object using Qt widgets
    """
    def __init__(self, report, parent=None, flat=False):
        super(ReportViewer, self).__init__(parent)
        self._flat = flat
        self._report = report

        layout = Qt.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(0, 1)

        self.csv_engine = CSVEngine()
        tables = {}
        self.csv_engine.collect_tables(self._report, tables)
        self.export_tables_window = ExportTablesPopup(tables=tables)
        self.export_tables_window.export_btn_clicked.connect(self._on_export_btn_clicked)

        vbox = Qt.QVBoxLayout()
        buttons = Qt.QWidget()
        buttons.setLayout(vbox)

        btn_group = Qt.QButtonGroup(buttons)
        btn = Qt.QPushButton(parent=self, icon=get_icon("scalable/document-save.svgz"), toolTip="Save HTML file...",
                             iconSize=Qt.QSize(32, 32))
        btn.clicked.connect(self._on_save)
        btn_group.addButton(btn, 1)
        vbox.addWidget(btn)

        btn = Qt.QPushButton(parent=self, icon=get_icon("scalable/export_table.svg"),
                             toolTip="Export tables to csv...", iconSize=Qt.QSize(32, 32))
        btn.clicked.connect(self.export_tables_window.show)
        btn_group.addButton(btn, 2)
        vbox.addWidget(btn)

        layout.addWidget(buttons, 0, 1, Qt.Qt.AlignTop)

        self._content = WebEngineView()
        self._content.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self._content, 0, 0)

        self.update_view(report)

    def update_view(self, report):
        """
        Update layout with the specified report
        :param report:
        """
        self._report = report

        # WA: using temp file instead of streams otherwise there are issues with large files
        fd, name = tempfile.mkstemp(suffix='.html')
        os.close(fd)
        with open(name, 'w') as stream:
            HtmlEngine(stream).render(report)
        self._content.load(Qt.QUrl.fromLocalFile(name))

    @slot
    def _on_load_finished(self, ok):
        if not ok:
            print("-E- Report load failed")

    @slot
    def _on_save(self):
        """
        Save report to an HTML file
        """
        file, _ = Qt.QFileDialog.getSaveFileName(self, "Export HTML file",
                                                 filter="HTML files (*.html);; All files (*)")
        if file is None or file == "":
            return

        with Wait():
            eng = HtmlEngine(file)
            eng.render(self._report)

        notify("Document saved")

    @slot
    def _on_export_btn_clicked(self):
        """
        Iterate over selected tables and export them to CSV.
        """
        directory = Qt.QFileDialog.getExistingDirectory(self, "Select Directory")
        if not directory:
            return
        self.export_tables_window.hide()
        self.csv_engine.set_dir_path(directory)
        tables_to_export = []
        for cb in self.export_tables_window.group_box.findChildren(Qt.QCheckBox):
            if cb.isChecked():
                tables_to_export.append(cb.text())

        if len(tables_to_export) < 1:
            return
        self.csv_engine.export_tables_to_csv(self._report, tables_to_export)
        notify(str(len(tables_to_export)) + ' csv files saved at ' + directory)


class ExportTablesPopup(Qt.QDialog):
    """
    Class which generate a pop-up window to select tables from the report to export
    """

    def __init__(self, parent=None, tables=None):
        super().__init__(parent)
        self.setMaximumWidth(250)
        self.setMaximumHeight(500)
        self.setModal(True)
        self.tables = tables
        self.setWindowTitle('Tables Export')
        layout = Qt.QVBoxLayout()
        self.setLayout(layout)

        self.label = Qt.QLabel('Select tables to export:')
        layout.addWidget(self.label)

        self.group_box = Qt.QGroupBox()
        scroll_area_layout = Qt.QVBoxLayout()
        for table in self.tables.keys():
            check_box = Qt.QCheckBox(table)
            scroll_area_layout.addWidget(check_box)
        self.group_box.setLayout(scroll_area_layout)

        scroll_area = Qt.QScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.group_box)
        layout.addWidget(scroll_area)

        buttons = Qt.QDialogButtonBox(parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        btn = buttons.addButton('Export', Qt.QDialogButtonBox.AcceptRole)
        btn.clicked.connect(self.export_btn_clicked.emit)
        buttons.addButton(Qt.QDialogButtonBox.Cancel)

        layout.addWidget(buttons)

    export_btn_clicked = Qt.pyqtSignal()
