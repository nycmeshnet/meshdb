from django.contrib import admin
from django.urls import path, re_path
from django.views.generic.base import RedirectView

from meshapi.admin.password_reset import (
    AdminPasswordResetCompleteView,
    AdminPasswordResetConfirmView,
    AdminPasswordResetDoneView,
    AdminPasswordResetView,
)
from meshdb.views import admin_iframe_view, minimal_example_view, redirect_admin

urlpatterns = [
    path("password_reset/", AdminPasswordResetView.as_view(), name="admin_password_reset"),
    path("password_reset/done/", AdminPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password_reset/<uidb64>/<token>/", AdminPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password_reset/done/", AdminPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("panel/", admin.site.urls),
    #path("", admin_iframe_view),
    path("minimal_example/", minimal_example_view),
    re_path(r'^(?P<path>.*)$', admin_iframe_view),  # Match any other /admin/* URL
]
