from django import forms
from django.contrib import admin

from meshapi.admin.inlines import InstallInline
from meshapi.models import Member


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
class MemberAdmin(admin.ModelAdmin):
    form = MemberAdminForm
    search_fields = [
        # Search by name
        "name__icontains",
        "primary_email_address__icontains",
        "stripe_email_address__icontains",
        "additional_email_addresses__icontains",
        "phone_number__icontains",
        "slack_handle__icontains",
        # Search by building details
        "installs__building__street_address__icontains",
        "installs__building__city__iexact",
        "installs__building__state__iexact",
        "installs__building__zip_code__iexact",
        "installs__building__bin__iexact",
        # Search by network number
        "installs__node__network_number__iexact",
        "installs__install_number__iexact",
        # Notes
        "notes__icontains",
    ]
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
