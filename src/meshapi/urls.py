from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from meshapi import views

urlpatterns = [
    path("", views.api_root),
    path("auth/", include("rest_framework.urls")),
    path("users/", views.UserList.as_view(), name="meshapi-v1-user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="meshapi-v1-user-detail"),
    path("buildings/", views.BuildingList.as_view(), name="meshapi-v1-building-list"),
    path("buildings/<int:pk>/", views.BuildingDetail.as_view(), name="meshapi-v1-building-detail"),
    path("members/", views.MemberList.as_view(), name="meshapi-v1-member-list"),
    path("members/<int:pk>/", views.MemberDetail.as_view(), name="meshapi-v1-member-detail"),
    path("installs/", views.InstallList.as_view(), name="meshapi-v1-install-list"),
    path("installs/<int:pk>/", views.InstallDetail.as_view(), name="meshapi-v1-install-detail"),
    path("requests/", views.RequestList.as_view(), name="meshapi-v1-request-list"),
    path("requests/<int:pk>/", views.RequestDetail.as_view(), name="meshapi-v1-request-detail"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
