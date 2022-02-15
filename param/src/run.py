import comms_wrapper
import sys
path ="../../micro_service/analysis"
if path not in sys.path:
    sys.path.append(path)

from utils import read_config
#from dl-modeling.micro_service.analysis.utils import *

a=read_config("/home/sdg3/param/dl-modeling/modelzoo/config.csv")
b=read_config("/home/sdg3/param/dl-modeling/modelzoo/config_scaleout.csv")
a['outFilePath']='./'
a['frequency_in_Ghz'] = 1.7
comms_wrapper.comms_wrapper(a,"/home/sdg3/param/dl-modeling/micro_service/analysis/comms.csv",
                            "/home/sdg3/param/dl-modeling/micro_service/analysis/compute.csv",
                            "./out.csv",
                            "/home/sdg3/param/dl-modeling/micro_service/analysis/TransformerLanguageModel_17B.py_graph_out.json",
                            1,
                            b)