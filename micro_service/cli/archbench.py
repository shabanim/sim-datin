from cli import ICommandLineHandler
from analysis.summary import archbench
import argparse


class ArchbenchCLIHandler(ICommandLineHandler):
    @staticmethod
    def get_command():
        return "archbench"

    def __init__(self):
        pass

    def description(self):
        return "Invoke single instance of archbench over given config files and generate report"

    def exec(self, argv):
        args = self._parse_command_line_args(argv)
        archbench(args.workload_graph, args.archbench_config)

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(prog="./micro_service/dl-modelling.py {}".format(ArchbenchCLIHandler.get_command()),
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-f', '--workload_graph', type=str)
        parser.add_argument('-cf', '--archbench_config', type=str)
        args = parser.parse_args(argv)
        return args