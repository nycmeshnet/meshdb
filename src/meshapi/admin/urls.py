from django.contrib import admin
from django.urls import path

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
    path("iframe_wrapper/", admin_iframe_view),
    path("", admin.site.urls),
]
