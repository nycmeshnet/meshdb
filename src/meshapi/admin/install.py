from django.contrib import admin
from django.contrib.admin.options import forms
from django.db.models import Q
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector
from meshapi.widgets import DeviceIPAddressWidget, PanoramaViewer
from meshapi.admin.inlines import *




class InstallAdminForm(forms.ModelForm):
    class Meta:
        model = Install
        fields = "__all__"
        widgets = {
            "unit": forms.TextInput(),
        }


@admin.register(Install)
class InstallAdmin(admin.ModelAdmin):
    form = InstallAdminForm
    list_filter = [
        ("node", admin.EmptyFieldListFilter),
        "status",
        "request_date",
        "install_date",
        "abandon_date",
    ]
    list_display = ["__str__", "status", "node", "member", "building", "unit"]
    search_fields = [
        # Install number
        "install_number__iexact",
        "node__network_number__iexact",
        # Search by building details
        "building__street_address__icontains",
        "building__city__iexact",
        "building__state__iexact",
        "building__zip_code__iexact",
        "building__bin__iexact",
        # Search by member details
        "member__name__icontains",
        "member__primary_email_address__icontains",
        "member__phone_number__iexact",
        "member__slack_handle__iexact",
        # Notes
        "notes__icontains",
    ]
    autocomplete_fields = ["building", "member"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "status",
                    "ticket_id",
                    "member",
                ]
            },
        ),
        (
            "Node",
            {
                "fields": [
                    "node",
                ]
            },
        ),
        (
            "Building",
            {
                "fields": [
                    "building",
                    "unit",
                    "roof_access",
                ]
            },
        ),
        (
            "Dates",
            {
                "fields": [
                    "request_date",
                    "install_date",
                    "abandon_date",
                ],
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "diy",
                    "referral",
                    "notes",
                ]
            },
        ),
    ]

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            upper_search = search_term.upper()
            if len(upper_search) > 2 and upper_search[:2] == "NN":
                search_term_as_int = int(upper_search[2:])
                queryset |= self.model.objects.filter(node_id=search_term_as_int)
        except ValueError:
            pass
        return queryset, may_have_duplicates


