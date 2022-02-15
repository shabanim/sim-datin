import os, shutil
import subprocess
import tempfile
from unittest import TestCase
from utils import html_file_compare, csv_file_compare
from testcontext import PROJECT_DIR, EXPECTED_DIR, DATA_DIR, RESULTS_DIR, updateGroundTruthFile


class TestSummaryCli(TestCase):
    """
    Test case to perform regression of param-runner
    """

    def test_summary_bert(self):
        if (os.path.exists(RESULTS_DIR)):
            shutil.rmtree(RESULTS_DIR)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'summary',
            '-pc', "{}".format(os.path.join(DATA_DIR, 'bert', 'BERT-LARGE-SEQ512-BF16_PVCC_90Ser.yml')),
            '-po', "{}".format(os.path.join(RESULTS_DIR ,'Report.csv')),
            '-g', "{}".format(os.path.join(DATA_DIR, 'Gen12-SKUs-PVC.xlsx')),  # PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
            '-w', "{}".format(os.path.join(DATA_DIR, 'PVC-Workloads.xlsx')),  # PVC-AtScale-Workloads.xlsx
            '-i', 'FALSE',
            '-t', 'TRUE',
            '--compderate', '0.95',
            '--fusion', 'workload',
            '--pipeline-backward-pass', 'TRUE',
            '--flush-oversized-output-tensor', 'TRUE',
            '--frequency', "{}".format(1400), "{}".format(1500), "{}".format(100),
            '-o', "{}".format(RESULTS_DIR),
            '-s', 'AGGR',
            '-a', 'run',
            '--filtersku', "{}".format('PVC1T-512-C0-85-80'),
            '--filter', "{}".format('BERT-LARGE-SEQ512-BF16'),
            '--dump_html'
        ]
        subprocess.check_call(cmd)

        expected_file = os.path.join(EXPECTED_DIR, 'bert', 'SpeedSim_TaskAnalysis.csv')
        result_file = os.path.join(PROJECT_DIR, 'modelzoo' , 'SpeedSim_TaskAnalysis.csv')
        if updateGroundTruthFile:
            shutil.copyfile(result_file,expected_file)
        else:
            self.assertTrue(csv_file_compare(result_file, expected_file), msg="Comparing " + result_file + " " + expected_file)

    def test_summary_transformer_1T(self):
        if (os.path.exists(RESULTS_DIR)):
            shutil.rmtree(RESULTS_DIR)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'summary',
            '-pc',
            "{}".format(os.path.join(DATA_DIR, '1T_transformer', 'TransformerLanguageModel_1T_PVCC_90Ser.yml')),
            '-po', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
            '-g', "{}".format(os.path.join(DATA_DIR, 'Gen12-SKUs-PVC.xlsx')),  # PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
            '-w', "{}".format(os.path.join(DATA_DIR, 'PVC-Workloads.xlsx')),  # PVC-AtScale-Workloads.xlsx
            '-i', 'FALSE',
            '-t', 'TRUE',
            '--compderate', '0.95',
            '--fusion', 'workload',
            '--pipeline-backward-pass', 'TRUE',
            '--flush-oversized-output-tensor', 'TRUE',
            '--frequency', "{}".format(1400), "{}".format(1500), "{}".format(100),
            '-o', "{}".format(RESULTS_DIR),
            '-s', 'AGGR',
            '-a', 'run',
            '--filtersku', "{}".format('PVC1T-512-C0-85-80'),
            '--filter', "{}".format('TransformerLanguageModel_1T_meg'),
            '--dump_html'
        ]
        subprocess.check_call(cmd)

        expected_file = os.path.join(EXPECTED_DIR, '1T_transformer', 'SpeedSim_TaskAnalysis.csv')
        result_file = os.path.join(PROJECT_DIR, 'modelzoo', 'SpeedSim_TaskAnalysis.csv')
        if updateGroundTruthFile:
            shutil.copyfile(result_file, expected_file)
        else:
            self.assertTrue(csv_file_compare(result_file, expected_file),
                            msg="Comparing " + result_file + " " + expected_file)

    def test_summary_transformer_1T_zinf(self):
        if (os.path.exists(RESULTS_DIR)):
            shutil.rmtree(RESULTS_DIR)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'summary',
            '-pc',
            "{}".format(os.path.join(DATA_DIR, '1T_transformer_zinf', 'TransformerLanguageModel_1T_PVCC_opt_glueless.yml')),
            '-po', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
            '-g', "{}".format(os.path.join(DATA_DIR, 'Gen12-SKUs-PVC.xlsx')),  # PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
            '-w', "{}".format(os.path.join(DATA_DIR, 'PVC-Workloads.xlsx')),  # PVC-AtScale-Workloads.xlsx
            '-i', 'FALSE',
            '-t', 'TRUE',
            '--compderate', '0.95',
            '--fusion', 'workload',
            '--pipeline-backward-pass', 'TRUE',
            '--flush-oversized-output-tensor', 'TRUE',
            '--frequency', "{}".format(1400), "{}".format(1500), "{}".format(100),
            '-o', "{}".format(RESULTS_DIR),
            '-s', 'AGGR',
            '-a', 'run',
            '--filtersku', "{}".format('PVC1T-512-C0-85-80'),
            '--filter', "{}".format('TransformerLanguageModel_1T_zinf'),
            '--dump_html'
        ]
        subprocess.check_call(cmd)

        expected_file = os.path.join(EXPECTED_DIR, '1T_transformer_zinf', 'SpeedSim_TaskAnalysis.csv')
        result_file = os.path.join(PROJECT_DIR, 'modelzoo', 'SpeedSim_TaskAnalysis.csv')
        if updateGroundTruthFile:
            shutil.copyfile(result_file, expected_file)
        else:
            self.assertTrue(csv_file_compare(result_file, expected_file),
                            msg="Comparing " + result_file + " " + expected_file)


    def test_summary_transformer_1T_pod(self):
        if (os.path.exists(RESULTS_DIR)):
            shutil.rmtree(RESULTS_DIR)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'summary',
            '-pc',
            "{}".format(
                os.path.join(DATA_DIR, '1T_transformer_pod', 'TransformerLanguageModel_1T_PVCC_90Ser.yml')),
            '-po', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
            '-g', "{}".format(os.path.join(DATA_DIR, 'Gen12-SKUs-PVC.xlsx')),  # PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
            '-w', "{}".format(os.path.join(DATA_DIR, 'PVC-Workloads.xlsx')),  # PVC-AtScale-Workloads.xlsx
            '-i', 'FALSE',
            '-t', 'TRUE',
            '--compderate', '0.95',
            '--fusion', 'workload',
            '--pipeline-backward-pass', 'TRUE',
            '--flush-oversized-output-tensor', 'TRUE',
            '--frequency', "{}".format(1400), "{}".format(1500), "{}".format(100),
            '-o', "{}".format(RESULTS_DIR),
            '-s', 'AGGR',
            '-a', 'run',
            '--filtersku', "{}".format('PVC1T-512-C0-85-80'),
            '--filter', "{}".format('TransformerLanguageModel_1T_meg'),
            '--dump_html'
        ]
        subprocess.check_call(cmd)

        expected_file = os.path.join(EXPECTED_DIR, '1T_transformer_pod', 'SpeedSim_TaskAnalysis.csv')
        result_file = os.path.join(PROJECT_DIR, 'modelzoo', 'SpeedSim_TaskAnalysis.csv')
        if updateGroundTruthFile:
            shutil.copyfile(result_file, expected_file)
        else:
            self.assertTrue(csv_file_compare(result_file, expected_file),
                            msg="Comparing " + result_file + " " + expected_file)


    def test_summary_transformer_175B(self):
        if (os.path.exists(RESULTS_DIR)):
            shutil.rmtree(RESULTS_DIR)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'summary',
            '-pc', "{}".format(os.path.join(DATA_DIR, '175B_transformer', 'TransformerLanguageModel_175B_PVCC_90Ser.yml')),
            '-po', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
            '-g', "{}".format(os.path.join(DATA_DIR, 'Gen12-SKUs-PVC.xlsx')),  # PVC-Kicker.xlsx Gen12-SKUs-PVC.xlsx
            '-w', "{}".format(os.path.join(DATA_DIR, 'PVC-Workloads.xlsx')),  # PVC-AtScale-Workloads.xlsx
            '-i', 'FALSE',
            '-t', 'TRUE',
            '--compderate', '0.95',
            '--fusion', 'workload',
            '--pipeline-backward-pass', 'TRUE',
            '--flush-oversized-output-tensor', 'TRUE',
            '--frequency', "{}".format(1400), "{}".format(1500), "{}".format(100),
            '-o', "{}".format(RESULTS_DIR),
            '-s', 'AGGR',
            '-a', 'run',
            '--filtersku', "{}".format('PVC1T-512-C0-85-80'),
            '--filter', "{}".format('TransformerLanguageModel_175B'),
            '--dump_html'
        ]
        subprocess.check_call(cmd)


        expected_file = os.path.join(EXPECTED_DIR, '175B_transformer', 'SpeedSim_TaskAnalysis.csv')
        result_file = os.path.join(PROJECT_DIR, 'modelzoo', 'SpeedSim_TaskAnalysis.csv')
        if updateGroundTruthFile:
            shutil.copyfile(result_file, expected_file)
        else:
            self.assertTrue(csv_file_compare(result_file, expected_file),
                            msg="Comparing " + result_file + " " + expected_file)

    # def test_param_bert(self):
    #
    #     cmd = [
    #         'python', './micro_service/dl-modelling.py', 'param',
    #         '-f', "{}".format(os.path.join(DATA_DIR, 'bert', 'BERT_enc_s512_lay24_c13_h16.py')),
    #         '-cf', "{}".format(os.path.join(DATA_DIR, 'bert', 'GEN_PVC1T.yaml')),
    #         '-c', "{}".format(os.path.join(DATA_DIR, 'bert', 'base_param_cfg.yml')),
    #         '-o', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
    #         '--training', '-ssd'
    #     ]
    #     subprocess.check_call(cmd)
    #
    #     expected_file = os.path.join(EXPECTED_DIR, 'bert', 'Report.csv')
    #     result_file = os.path.join(RESULTS_DIR, 'Report.csv')
    #     self.assertTrue(csv_file_compare(result_file, expected_file), msg="Comparing " + result_file + " " + expected_file)
    #
    # def test_dlrm_ml_perf(self):
    #
    #     cmd = [
    #         'python', './micro_service/dl-modelling.py', 'summary',
    #         '-f', "{}".format(os.path.join(DATA_DIR, 'dlrm_ml_perf', 'DLRM_inference_mlperf.py')),
    #         '-cf', "{}".format(os.path.join(DATA_DIR, 'dlrm_ml_perf', 'GEN_PVC1T.yaml')),
    #         '-c', "{}".format(os.path.join(DATA_DIR, 'dlrm_ml_perf', 'base_param_cfg.yml')),
    #         '-o', "{}".format(os.path.join(RESULTS_DIR, 'Report.csv')),
    #         '--training', '--trg-optimizer', 'sgd', '--dump_html'
    #     ]
    #     subprocess.check_call(cmd)
    #
    #     expected_file = os.path.join(EXPECTED_DIR, 'dlrm_ml_perf', 'Report.csv')
    #     result_file = os.path.join(RESULTS_DIR, 'Report.csv')
    #     self.assertTrue(csv_file_compare(result_file, expected_file),
    #                     msg="Comparing " + result_file + " " + expected_file)


if __name__ == '__main__':
    import unittest
    unittest.main()