from typing import Any, Optional, Type

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Device
from meshapi.widgets import AutoPopulateLocationWidget, DeviceIPAddressWidget


class DeviceAdminForm(forms.ModelForm):
    auto_populate_location_field = forms.Field(
        required=False,
        widget=AutoPopulateLocationWidget("Node"),
    )

    class Meta:
        model = Device
        fields = "__all__"
        widgets = {
            "ip_address": DeviceIPAddressWidget(),
        }


@admin.register(Device)
class DeviceAdmin(ImportExportModelAdmin, ExportActionMixin):
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
    fieldsets = [
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
                    "model",
                    "type",
                    "uisp_id",
                    "notes",
                ]
            },
        ),
    ]
    inlines = [DeviceLinkInline]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        return form

    def get_queryset(self, request: HttpRequest) -> QuerySet[Device]:
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset
