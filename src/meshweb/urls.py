from django.urls import path

from meshweb import views

urlpatterns = [
    path("", views.index, name="main"),
    path("maintenance/", views.maintenance, name="maintenance"),
    path("enable-maintenance/", views.enable_maintenance, name="enable-maintenance"),
    path("disable-maintenance/", views.disable_maintenance, name="disable-maintenance"),
]
