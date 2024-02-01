from django.urls import path, include
from meshweb import views

urlpatterns = [
    path("", views.index, name='main'),
]
