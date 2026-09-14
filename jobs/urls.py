from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("status/<int:pk>/", views.StatusView.as_view(), name="status"),
    path("jobs/", views.JobListView.as_view(), name="job-list"),
    path("ask/", views.AskView.as_view(), name="ask"),
    path("events/<int:pk>/", views.EventsView.as_view(), name="events"),
]