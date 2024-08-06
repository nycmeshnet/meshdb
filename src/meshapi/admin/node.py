from typing import Any, Optional, Type

import tablib
from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from import_export import resources
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.inlines import (
    BuildingMembershipInline,
    DeviceInline,
    InstallInline,
    NodeLinkInline,
    NonrelatedBuildingInline,
    PanoramaInline,
    SectorInline,
)
from meshapi.models import Building, Node
from meshapi.widgets import AutoPopulateLocationWidget

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"


class NodeImportExportResource(resources.ModelResource):
    def before_import(self, dataset: tablib.Dataset, **kwargs: Any) -> None:
        if "network_number" not in dataset.headers:
            dataset.headers.append("network_number")
        super().before_import(dataset, **kwargs)

    class Meta:
        model = Node
        import_id_fields = ("network_number",)


class NodeAdminForm(forms.ModelForm):
    auto_populate_location_field = forms.Field(
        required=False,
        widget=AutoPopulateLocationWidget("Building"),
    )

    class Meta:
        model = Node
        fields = "__all__"


@admin.register(Node)
class NodeAdmin(ImportExportModelAdmin, ExportActionMixin):
    form = NodeAdminForm
    resource_classes = [NodeImportExportResource]
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
                    "auto_populate_location_field",
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
        PanoramaInline,
        InstallInline,
        NonrelatedBuildingInline,
        BuildingMembershipInline,
        DeviceInline,
        SectorInline,
        NodeLinkInline,
    ]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        return form

    def address(self, obj: Node) -> Optional[Building]:
        return obj.buildings.first()
