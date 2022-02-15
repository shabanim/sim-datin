from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Summary
from .viewmodels import summary_task


def index(request):
    latest_summary_runs = Summary.objects.order_by("-run_issue_date")
    context = {"latest_summary_runs": latest_summary_runs}
    return render(request, "dlmodeling/index.html", context)

def summary_request(request):
    return render(request, "dlmodeling/summary_request.html", {})

def summary_run(request):
    if request.method == 'POST':
        s = Summary.from_request(request)
        summary_task(s)
    return HttpResponseRedirect(reverse('dlmodeling:index'))