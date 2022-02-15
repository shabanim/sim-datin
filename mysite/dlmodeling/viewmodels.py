import csv
import os
import sys
from threading import Thread
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

if os.name == "nt":
    ms_path = '..\\micro_service\\'
    param_path = '..\\param\\'
    ss_path = "..\\speedsim"
else:
    ms_path = '../micro_service/'
    param_path = '../param/'
    ss_path = "../speedsim"

sys.path.append(ms_path)
sys.path.append(param_path)
sys.path.append(ss_path)

from .models import Summary
from analysis.utils import get_config_df
from analysis.summary import summary as summary_analysis
from report_objects import format_summary_report
from reports import render_report


def fs_read_config(fname):
    if fname is None:
        return None
    with FileSystemStorage().open(name=fname.name, mode="r") as fin:
        reader = csv.reader(fin)
        return {row[0]: row[1] for row in reader if len(row) > 0}


def summary_work(summary_model_obj: Summary):
    summary_model_obj.status = Summary.STATUS.EXE
    summary_model_obj.save()

    config_dict = fs_read_config(summary_model_obj.param_scaleup_config)
    scaleout_dict = fs_read_config(summary_model_obj.param_scaleout_config)

    fs = FileSystemStorage()
    param_report = fs.url(fs.save(name="Report.csv", content=ContentFile("")))

    overlap_summary = summary_analysis(summary_model_obj.workload_graph.name,
                                       summary_model_obj.archbench_config.name,
                                       config_dict,
                                       param_report,
                                       scaleout_dict,
                                       summary_model_obj.enable_scaleout)
    config_df = get_config_df(config_dict, scaleout_dict,
                              summary_model_obj.enable_scaleout)
    summary_model_obj.config_df = config_df.to_json(orient="records")
    summary_model_obj.run_summary_df = overlap_summary.info_df.to_json(orient="records")
    report = format_summary_report(config_df, overlap_summary)

    speedsim_outpath = fs.url(fs.save(name="SpeedSimAnalysis.html", content=ContentFile("")))
    render_report(report, speedsim_outpath)
    summary_model_obj.param_report = param_report
    summary_model_obj.overlap_report = speedsim_outpath

    summary_model_obj.status = Summary.STATUS.COMPLETED
    summary_model_obj.save()


def summary_task(summary_model_obj: Summary):
    """
    Async task to execute summary command, dont add any logic to this,
    should return as soon as worker thread is started
    :param s: of type Summary model
    :return: None
    """
    task = Thread(target=summary_work,
                  kwargs=dict(summary_model_obj=summary_model_obj))
    task.start()

    return
