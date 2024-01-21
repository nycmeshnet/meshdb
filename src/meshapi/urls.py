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
    path("join/", views.join_form, name="meshapi-v1-join"),
    path("nn-assign/", views.network_number_assignment, name="meshapi-v1-nn-assign"),
    path("member/lookup/", views.LookupMember.as_view(), name="meshapi-v1-lookup-member"),
    path("install/lookup/", views.LookupInstall.as_view(), name="meshapi-v1-lookup-install"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
