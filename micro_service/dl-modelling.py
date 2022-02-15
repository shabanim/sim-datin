import sys
import os

paths = ["speedsim", "param"]
for path in paths:
    if os.name == "nt":
        import_path = '.\\{}\\'.format(path)
    else:
        import_path = './{}/'.format(path)
    if path not in sys.path:
        sys.path.append(import_path)

from cli import SummaryCLIHandler
from cli import LoopCLIHandler
from cli import ParamCLIHandler
from cli import ArchbenchCLIHandler
from cli import UploadConfig
from cli import UploadResult
from cli import UbenchCLIHandler

class DlModellingApp:
    def __init__(self, argv):
        self._argv = argv

    def exec(self):
        subcommand = self._argv[1]
        if subcommand == SummaryCLIHandler.get_command():
            summaryhandler = SummaryCLIHandler()
            summaryhandler.exec(argv=self._argv[2:])
        elif subcommand == LoopCLIHandler.get_command():
            loophandler = LoopCLIHandler()
            loophandler.exec(argv=self._argv[2:])
        elif subcommand == ParamCLIHandler.get_command():
            paramhandler = ParamCLIHandler()
            paramhandler.exec(argv=self._argv[2:])
        elif subcommand == ArchbenchCLIHandler.get_command():
            archbenchhandler = ArchbenchCLIHandler()
            archbenchhandler.exec(argv=self._argv[2:])
        elif subcommand == UploadConfig.get_command():
            upload_config = UploadConfig()
            upload_config.exec(argv=self._argv[2:])
        elif subcommand == UploadResult.get_command():
            upload_result = UploadResult()
            upload_result.exec(argv=self._argv[2:])
        elif subcommand == UbenchCLIHandler.get_command():
            ubench = UbenchCLIHandler()
            ubench.exec(argv=self._argv[2:])
        else:
            print("Unknown subcommand {}".format(subcommand))


if __name__ == "__main__":
    res = DlModellingApp(sys.argv).exec()
    import gc
    gc.collect()  # need this to terminate streams / threads that might be cleaned by __del__
    sys.exit(res)