import os
import argparse

from cli import ICommandLineHandler
from analysis.summary import summary
from analysis.utils import read_config, get_config_df
from reports import render_report
from report_objects import format_summary_report
from src.knobs import Knobs
from time import time


parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ab_automation_dir = os.path.join(parent_dir, 'ab-release-automation')

def str_to_boolean(s):
    if isinstance(s, bool):
        return s
    if s.lower() in ['true', 't', 'yes', 'y', 'on', 'enable']:
        return True
    elif s.lower() in ['false', 'f', 'no', 'n', 'off', 'disable']:
        return False
    else:
        raise argparse.ArgumentTypeError('expecting boolean value')

MASTER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SummaryCLIHandler(ICommandLineHandler):
    """
    invoke single instance of dl-modelling over given config files and generate report
    """
    @staticmethod
    def get_command():
        return "summary"

    def __init__(self):
        pass

    def description(self):
        return "Invoke single instance of dl-modelling over given config files and generate summary report"



    def exec(self, argv):
        (args, ab_args) = self._parse_command_line_args(argv)

        knobs = Knobs(args.param_config)
        overlap_summary = summary(ab_args, args.param_config, args.param_outputfile,
                                  args.fabsim_trace, args.fabsim_scaleup_run_log,
                                  args.fabsim_scaleout_run_log, args.param_detailed_report,
                                  args.upload)
        config_df = get_config_df(knobs)
        start_secs = time()
        report = format_summary_report(config_df, overlap_summary, args.param_detailed_report)
        try:
            outFilePath = knobs["outFilePath"]
        except:
            outFilePath = "./"

        render_report(report, "{}SpeedSimAnalysis.html".format(outFilePath))
        print("Report rendering: Completed jobb in {}".format(time() - start_secs))
        print("Summary executed")

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(prog="./micro_service/dl-modelling.py {}".format(SummaryCLIHandler.get_command()),
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--param-outputfile', '-po', type=str, default="Report.csv")
        parser.add_argument('--param-config', '-pc', help='Specify the configuration .yaml to use)')
        parser.add_argument('--param-detailed-report', '-pdr', action='store_true',
                            help='Include speedsim detailed results')
        parser.add_argument('--upload', '-up', action='store_true', help='Upload results to database')
        parser.add_argument('-ft', '--fabsim_trace', type=str)
        parser.add_argument('-fsurl', '--fabsim_scaleup_run_log', type=str)
        parser.add_argument('-fsorl', '--fabsim_scaleout_run_log', type=str)

        args, ab_args = parser.parse_known_args(argv)

        return (args, ab_args)
