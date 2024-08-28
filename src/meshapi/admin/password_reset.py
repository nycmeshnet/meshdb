from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)


class AdminPasswordResetView(PasswordResetView):
    subject_template_name = "admin/password_reset/password_reset_email_subject.txt"
    html_email_template_name = "admin/password_reset/password_reset_email.html"
    template_name = "admin/password_reset/password_reset_form.html"


class AdminPasswordResetDoneView(PasswordResetDoneView):
    template_name = "admin/password_reset/password_reset_done.html"


class AdminPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "admin/password_reset/password_reset_confirm.html"


class AdminPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "admin/password_reset/password_reset_complete.html"
