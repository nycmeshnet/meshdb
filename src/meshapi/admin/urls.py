from django.contrib import admin
from django.urls import path

from meshapi.admin.password_reset import (
    AdminPasswordResetCompleteView,
    AdminPasswordResetConfirmView,
    AdminPasswordResetDoneView,
    AdminPasswordResetView,
)

urlpatterns = [
    path("admin/password_reset/", AdminPasswordResetView.as_view(), name="admin_password_reset"),
    path("admin/password_reset/done/", AdminPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", AdminPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", AdminPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("", admin.site.urls),
]
