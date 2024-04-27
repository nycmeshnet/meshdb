from django.contrib import admin
from django.contrib.admin.options import forms
from django.db.models import Q
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector
from meshapi.widgets import DeviceIPAddressWidget, PanoramaViewer
from meshapi.admin.inlines import *

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"

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


class LinkAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = "__all__"
        widgets = {
            "description": forms.TextInput(),
        }


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    form = LinkAdminForm
    search_fields = [
        "from_device__node__name__icontains",
        "to_device__node__name__icontains",
        "from_device__node__buildings__street_address__icontains",
        "to_device__node__buildings__street_address__icontains",
        "from_device__node__network_number__iexact",
        "to_device__node__network_number__iexact",
        "notes__icontains",
    ]
    list_display = ["__str__", "status", "from_device", "to_device", "description"]
    list_filter = ["status", "type"]

    autocomplete_fields = ["from_device", "to_device"]

device_fieldsets = [
    (
        "Details",
        {
            "fields": [
                "status",
                "name",
                "ssid",
                "ip_address",
                "node",
            ]
        },
    ),
    (
        "Location",
        {
            "fields": [
                "latitude",
                "longitude",
                "altitude",
            ]
        },
    ),
    (
        "Dates",
        {
            "fields": [
                "install_date",
                "abandon_date",
            ]
        },
    ),
    (
        "Misc",
        {
            "fields": [
                "model",
                "type",
                "uisp_id",
                "notes",
            ]
        },
    ),
]


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"
        widgets = {
            "ip_address": DeviceIPAddressWidget(),
        }


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    search_fields = ["name__icontains", "model__icontains", "ssid__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "model",
    ]
    list_filter = [
        "status",
        "install_date",
        "model",
    ]
    fieldsets = device_fieldsets
    inlines = [DeviceLinkInline]

    def get_queryset(self, request):
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset


class SectorAdminForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = "__all__"


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    form = SectorAdminForm
    search_fields = ["name__icontains", "model__icontains", "ssid__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "model",
    ]
    list_filter = [
        "status",
        "install_date",
        "model",
    ]
    inlines = [DeviceLinkInline]
    fieldsets = device_fieldsets + [
        (
            "Sector Attributes",
            {
                "fields": [
                    "radius",
                    "azimuth",
                    "width",
                ]
            },
        ),
    ]
