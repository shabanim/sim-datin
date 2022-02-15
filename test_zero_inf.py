import os
import subprocess
import sys
import tempfile
import filecmp
from unittest import TestCase
from utils import html_file_compare, csv_file_compare
from testcontext import PROJECT_DIR, EXPECTED_DIR, DATA_DIR, RESULTS_DIR

class TestParser(TestCase):

    def test_zero_inf(self):
        cmd = [
            'python', os.path.join(PROJECT_DIR, 'micro_service', 'analysis', 'overlap_zero_inf.py'),
            '--workload-json', os.path.join(DATA_DIR, 'zero-inf', 'TransformerLanguageModel_1T.py_graph_out.json'),
            '--knobs-yaml', os.path.join(DATA_DIR, 'zero-inf', 'base_param_cfg.yml'),
        ]
        subprocess.check_call(cmd)
