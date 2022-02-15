import argparse



from cli import ICommandLineHandler


class UploadConfig(ICommandLineHandler):
    """
    Upload configs to PARAM_Config conduit container
    """
    @staticmethod
    def get_command():
        return "upload_config"

    def __init__(self):
        pass

    def description(self):
        return "Upload configs to PARAM_Config conduit container"

    def exec(self, argv):
        print("API deprecated !!")

    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(
            prog="./micro_service/dl-modelling.py {}".format(UploadConfig.get_command()),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('-workload', '--workload', type=str)
        parser.add_argument('-cards', '--cards', type=str)
        parser.add_argument('-tiles_per_card', '--tiles_per_card', type=str)
        parser.add_argument('-cfg_type', '--cfg_type', type=str,
                            choices=['Scaleup', 'Scaleout'])
        parser.add_argument('-cfg_file', '--cfg_file',type=str)
        parser.add_argument('-product_line', '--product_line', type=str)

        return parser.parse_args(argv)


