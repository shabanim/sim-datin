import argparse
import os
import sys

from cli import ICommandLineHandler


class UploadResult(ICommandLineHandler):
    """
    Upload configs to PARAM_Result conduit container
    """
    @staticmethod
    def get_command():
        return "upload_result"

    def __init__(self):
        pass

    def description(self):
        return "Upload results to PARAM_Results conduit container"

    def exec(self, argv):
        print("API deprecated!!")

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(
            prog="./micro_service/dl-modelling.py {}".format(UploadResult.get_command()),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('-product_line', '--product_line', type=str)
        parser.add_argument('-workload', '--workload', type=str)
        parser.add_argument('-cards', '--cards', type=str)
        parser.add_argument('-tiles_per_card', '--tiles_per_card', type=str)
        parser.add_argument('-result_type', '--result_type', type=str,
                            choices=['Archbench', 'Param', 'Overlap'])
        parser.add_argument('-result_file', '--result_file',type=str)

        return parser.parse_args(argv)


