import os
import subprocess
import tempfile
import filecmp
from unittest import TestCase
from utils import html_file_compare, csv_file_compare
from testcontext import PROJECT_DIR, EXPECTED_DIR, DATA_DIR, RESULTS_DIR

class TestParser(TestCase):

    def test_json_file(self):
        cmd = [
            'python', './micro_service/scripts/workload_parser.py',
            "{}".format(os.path.join(DATA_DIR, 'dlrm_ml_perf', 'dlrm_input.csv')),
            "{}".format(os.path.join(RESULTS_DIR, 'json_file.json')),
            "{}".format(os.path.join(RESULTS_DIR, 'layer_stats.csv')),
            "{}".format(os.path.join(RESULTS_DIR, 'stats.csv')),
        ]
        subprocess.check_call(cmd)

        expected_file = os.path.join(EXPECTED_DIR, 'dlrm_ml_perf', 'Layer_stats.csv')
        result_file = os.path.join(RESULTS_DIR, 'layer_stats.csv')
        self.assertTrue(filecmp.cmp(result_file, expected_file, shallow=False))

        #self.assertTrue(csv_file_compare(result_file, expected_file),
                       # msg="Comparing " + result_file + " " + expected_file)

        self.assertEqual(True, False)


if __name__ == '__main__':
    import unittest
    unittest.main()
