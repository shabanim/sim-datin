from cli import ICommandLineHandler
from analysis.summary import ubench
import argparse
from src.knobs import Knobs
import re

class UbenchCLIHandler(ICommandLineHandler):
    @staticmethod
    def get_command():
        return "ubench"

    def __init__(self):
        pass

    def description(self):
        return "Invoke single instance of param over given config files, for a single message size"

    def exec(self, argv):
        args, args_dict = self._parse_command_line_args(argv)
        knobs = Knobs(args.configfile)
        message_size = self.__get_message_size(args.message_size)
        print("Running message size: {} bytes".format(message_size))
        scaleup_time, scaleout_time = ubench(message_size, args.algo, knobs, args.outputfile)
        print("Scaleup time(ms) : {}".format(scaleup_time))
        print("Scaleout time(ms): {}".format(scaleout_time))

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(prog="./micro_service/dl-modelling.py {}".format(UbenchCLIHandler.get_command()),
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-m', '--message_size', type=str)
        parser.add_argument('-a', '--algo', type=str, default="allreduce")
        parser.add_argument('-c', '--configfile', type=str)
        parser.add_argument('-o', '--outputfile', type=str, default="Report.csv")
        args = parser.parse_args(argv)
        if args.algo not in ["allreduce", "a2a", "allgather", "gather", "scatter", "broadcast", "reducescatter", "reduce"]:
            raise ValueError("Algo {} cannot be handled".format(args.algo))
        return args, vars(args)
        
    __bytemul = {
        "" : 1,
        "k" : 1024,
        "m" : 1048576,
        "g" : 1073741824
    }

    def __get_message_size(self, str_ms):
        message = re.match("([0-9]*)([kmg]?)", str_ms.lower())
        ms = int(message[1])*int(self.__bytemul.get(message[2]))
        return ms