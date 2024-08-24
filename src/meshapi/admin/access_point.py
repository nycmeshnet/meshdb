from typing import Any, Optional, Type

from django.contrib import admin
from django.forms import Field, ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.device import DeviceAdmin, DeviceAdminForm
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import AccessPoint
from meshapi.widgets import AutoPopulateLocationWidget, DeviceIPAddressWidget


class AccessPointAdminForm(DeviceAdminForm):
    auto_populate_location_field = Field(
        required=False,
        widget=AutoPopulateLocationWidget("Node"),
    )

    class Meta:
        model = AccessPoint
        fields = "__all__"
        widgets = {
            "ip_address": DeviceIPAddressWidget(),
        }


@admin.register(AccessPoint)
class AccessPointAdmin(ImportExportModelAdmin, ExportActionMixin):
    form = AccessPointAdminForm
    search_fields = ["name__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "name",
        "node",
    ]
    list_filter = [
        "status",
        "install_date",
    ]
    inlines = [DeviceLinkInline]
    fieldsets = DeviceAdmin.fieldsets + [
        (
            "Location Attributes",
            {
                "fields": [
                    "auto_populate_location_field",
                    "latitude",
                    "longitude",
                    "altitude",
                ]
            },
        ),
    ]  # type: ignore[assignment]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        return form
