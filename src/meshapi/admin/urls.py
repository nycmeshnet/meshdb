from django.contrib import admin
from django.urls import path, re_path

from meshapi.admin.password_reset import (
    AdminPasswordResetCompleteView,
    AdminPasswordResetConfirmView,
    AdminPasswordResetDoneView,
    AdminPasswordResetView,
)
from meshdb.views import admin_iframe_view

urlpatterns = [
    path("password_reset/", AdminPasswordResetView.as_view(), name="admin_password_reset"),
    path("password_reset/done/", AdminPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password_reset/<uidb64>/<token>/", AdminPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password_reset/done/", AdminPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("panel/", admin.site.urls),
    re_path(r"^.*$", admin_iframe_view),  # Match any other /admin/* URL
]
