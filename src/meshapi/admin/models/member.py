from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.models import Member

from ..inlines import InstallInline
from ..ranked_search import RankedSearchMixin


class MemberAdminForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = "__all__"
        exclude = ["invalid"]
        widgets = {
            "name": forms.TextInput(),
            "phone_number": forms.TextInput(),
            "slack_handle": forms.TextInput(),
        }


@admin.register(Member)
class MemberAdmin(RankedSearchMixin, ImportExportModelAdmin, ExportActionMixin):
    form = MemberAdminForm
    search_fields = [
        # Search by name
        "name__icontains",
        "primary_email_address__icontains",
        "stripe_email_address__icontains",
        "additional_email_addresses__icontains",
        "phone_number__icontains",
        "additional_phone_numbers__icontains",
        "slack_handle__icontains",
        # Search by network number
        "installs__node__network_number__iexact",
        "installs__install_number__iexact",
        # Notes
        "@notes",
    ]
    search_vector = (
        SearchVector("name", weight="A")
        + SearchVector("primary_email_address", weight="A")
        + SearchVector("stripe_email_address", weight="A")
        + SearchVector("additional_email_addresses", weight="A")
        + SearchVector("phone_number", weight="A")
        + SearchVector("additional_phone_numbers", weight="A")
        + SearchVector("slack_handle", weight="A")
        + SearchVector("installs__node__network_number", weight="B")
        + SearchVector("installs__install_number", weight="B")
        + SearchVector("notes", weight="D")
    )
    list_display = [
        "__str__",
        "name",
        "primary_email_address",
        "stripe_email_address",
        "phone_number",
    ]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "name",
                ]
            },
        ),
        (
            "Email",
            {
                "fields": [
                    "primary_email_address",
                    "stripe_email_address",
                    "additional_email_addresses",
                ]
            },
        ),
        (
            "Contact Info",
            {
                "fields": [
                    "phone_number",
                    "additional_phone_numbers",
                    "slack_handle",
                ]
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "notes",
                ]
            },
        ),
    ]
    inlines = [InstallInline]
