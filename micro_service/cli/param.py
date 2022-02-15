from cli import ICommandLineHandler
from analysis.summary import param
import argparse
from analysis.utils import read_config, get_config_df
from report_objects import format_summary_report
from reports import render_report
from src.knobs import Knobs

class ParamCLIHandler(ICommandLineHandler):
    @staticmethod
    def get_command():
        return "param"

    def __init__(self):
        pass

    def description(self):
        return "Invoke single instance of param over given config files and generate report"

    def exec(self, argv):
        args, args_dict = self._parse_command_line_args(argv)
        knobs = Knobs(args.configfile)
        overlap_summary = param(args_dict, args.workload_graph, args.archbench_config, knobs, args.outputfile,
                                  args.ss_detailed_report)
        config_df = get_config_df(knobs)
        report = format_summary_report(config_df, overlap_summary, args.ss_detailed_report)
        try:
            outFilePath = knobs["outFilePath"]
        except:
            outFilePath = "./"

        render_report(report, "{}SpeedSimAnalysis.html".format(outFilePath))

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(prog="./micro_service/dl-modelling.py {}".format(ParamCLIHandler.get_command()),
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-f', '--workload_graph', type=str)
        parser.add_argument('-cf', '--archbench_config', type=str)
        parser.add_argument('-c', '--configfile', type=str)
        parser.add_argument('-ssd', '--ss_detailed_report', action='store_true',
                            help='include speedsim detailed results')
        parser.add_argument('-o', '--outputfile', type=str, default="Report.csv")
        parser.add_argument('--training', action='store_true', help='Do a training run')
        args = parser.parse_args(argv)
        return args, vars(args)
