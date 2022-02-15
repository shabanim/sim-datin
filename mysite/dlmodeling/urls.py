from django.urls import path

from . import views

app_name = "dlmodeling"
urlpatterns = [
    # ex: dlmodeling/
    path('', views.index, name='index'),

    # ex: dlmodeling/summary_request
    path('summary_request', views.summary_request, name='summary_request'),

    # ex: dlmodeling/summary_run
    path('summary_run', views.summary_run, name='summary_run'),
]