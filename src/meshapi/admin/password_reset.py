from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)


class AdminPasswordResetView(PasswordResetView):
    template_name = "admin/password_reset_form.html"


class AdminPasswordResetDoneView(PasswordResetDoneView):
    template_name = "admin/password_reset_done.html"


class AdminPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "admin/password_reset_confirm.html"


class AdminPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "admin/password_reset_complete.html"
