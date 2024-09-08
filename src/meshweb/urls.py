from django.urls import path

from meshweb import views

urlpatterns = [
    path("", views.index, name="main"),
    path("maintenance/", views.maintenance, name="maintenance"),
]
