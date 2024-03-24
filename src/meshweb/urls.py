from django.urls import include, path

from meshweb import views

urlpatterns = [
    path("", views.index, name="main"),
]
