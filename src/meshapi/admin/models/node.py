from typing import Any, List, Optional, Tuple, Type

import tablib
from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest
from import_export import resources
from import_export.admin import ExportActionMixin, ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import Building, Node
from meshapi.widgets import AutoPopulateLocationWidget, WarnAboutDatesWidget

from ..inlines import (
    AccessPointInline,
    BuildingMembershipInline,
    DeviceInline,
    InstallInline,
    NodeLinkInline,
    NonrelatedBuildingInline,
    PanoramaInline,
    SectorInline,
)
from ..ranked_search import RankedSearchMixin


class NodeImportExportResource(resources.ModelResource):
    def before_import(self, dataset: tablib.Dataset, **kwargs: Any) -> None:
        if "network_number" not in dataset.headers:
            dataset.headers.append("network_number")
        super().before_import(dataset, **kwargs)

    class Meta:
        model = Node
        import_id_fields = ("network_number",)


class NodeAdminForm(forms.ModelForm):
    validate_install_abandon_date_set_widget = forms.Field(
        required=False,
        widget=WarnAboutDatesWidget(),
    )

    auto_populate_location_field = forms.Field(
        required=False,
        widget=AutoPopulateLocationWidget("Building"),
    )

    class Meta:
        model = Node
        fields = "__all__"


@admin.register(Node)
class NodeAdmin(RankedSearchMixin, ExportActionMixin, ImportExportModelAdmin, SimpleHistoryAdmin):
    form = NodeAdminForm
    resource_classes = [NodeImportExportResource]
    search_fields = [
        "network_number__iexact",
        "name__icontains",
        "buildings__street_address__icontains",
        "@notes",
    ]
    search_vector = (
        SearchVector("network_number", weight="A")
        + SearchVector("name", weight="B")
        + SearchVector("buildings__street_address", weight="D")
        + SearchVector("notes", weight="D")
    )
    list_filter = ["status", ("name", admin.EmptyFieldListFilter), "install_date", "abandon_date"]
    list_display = ["__network_number__", "name", "status", "address", "install_date"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "network_number",
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
                    "placement",
                    "notes",
                    "validate_install_abandon_date_set_widget",
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
        AccessPointInline,
        NodeLinkInline,
    ]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        if "network_number" in form.base_fields:
            form.base_fields["network_number"].widget.attrs["style"] = "width: 7em;"
            form.base_fields["network_number"].help_text = (
                "If left blank, this will be auto-populated based on the next available NN "
                "(when status is set to Active)"
            )
            form.base_fields["network_number"].required = False
        return form

    def get_readonly_fields(self, request: HttpRequest, obj: Optional[Node] = None) -> List[str] | Tuple[str, ...]:
        if obj:  # obj is not None, so this is an edit
            return [
                "network_number",
            ] + list(super().get_readonly_fields(request, obj))
        else:
            return super().get_readonly_fields(request, obj)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("buildings")
            .prefetch_related("installs")
            .prefetch_related("devices")
        )

    def address(self, obj: Node) -> Optional[Building]:
        return obj.buildings.first()
