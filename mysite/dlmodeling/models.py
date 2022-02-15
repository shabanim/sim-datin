from django.db import models
from django.utils import timezone

from django.core.files.storage import FileSystemStorage


class Summary(models.Model):

    class STATUS:
        NEW = "New"
        EXE = "Executing"
        FAILED = "Failed"
        COMPLETED = "Completed"
        UNK = "Unknown"

    workload_graph = models.FileField()
    archbench_config = models.FileField()
    param_scaleup_config = models.FileField()
    enable_scaleout = models.BooleanField(default=False)
    param_scaleout_config = models.FileField(null=True)
    param_report = models.FileField(null=True)
    overlap_report = models.FileField(null=True)
    run_issue_date = models.DateTimeField(default=timezone.now())
    run_complete_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=25, default=STATUS.UNK)

    config_df = models.CharField(max_length=2048, null=True)
    run_summary_df = models.CharField(max_length=2048, null=True)

    @staticmethod
    def from_request(request):
        def _get_file(fname):
            return request.FILES[fname]

        if request.method == 'POST':
            fs = FileSystemStorage()
            s = Summary()

            s.workload_graph = fs.url(fs.save(None, _get_file('workload_graph'))) if \
                _get_file('workload_graph') else None

            s.archbench_config = fs.url(fs.save(None, _get_file('archbench_config'))) if \
                _get_file('archbench_config') else None

            s.param_scaleup_config = fs.url(fs.save(None, _get_file('scaleup_config'))) if \
                _get_file('scaleup_config') else None

            s.enable_scaleout = bool(request.POST.get('enable_scaleout'))

            s.param_scaleout_config = fs.url(fs.save(None,_get_file('scaleout_config'))) if \
                _get_file('scaleout_config') else None

            s.status = Summary.STATUS.NEW
            s.save()
            return s
        else:
            return None


