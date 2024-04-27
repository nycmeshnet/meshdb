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


class NodeAdminForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = "__all__"


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    form = NodeAdminForm
    search_fields = [
        "network_number__iexact",
        "name__icontains",
        "buildings__street_address__icontains",
        "notes__icontains",
    ]
    list_filter = ["status", ("name", admin.EmptyFieldListFilter), "install_date", "abandon_date"]
    list_display = ["__network_number__", "name", "status", "address", "install_date"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "status",
                    "type",
                    "name",
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
                    "notes",
                ]
            },
        ),
    ]
    inlines = [
        InstallInline,
        NonrelatedBuildingInline,
        BuildingMembershipInline,
        DeviceInline,
        SectorInline,
        NodeLinkInline,
    ]

    def address(self, obj):
        return obj.buildings.first()



