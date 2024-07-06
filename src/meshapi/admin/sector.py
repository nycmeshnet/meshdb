from typing import Any, Optional, Type

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.device import DeviceAdmin, DeviceAdminForm
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Sector


class SectorAdminForm(DeviceAdminForm):
    class Meta:
        model = Sector
        fields = "__all__"


@admin.register(Sector)
class SectorAdmin(ImportExportModelAdmin, ExportActionMixin):
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
    fieldsets = DeviceAdmin.fieldsets + [
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
    ]  # type: ignore[assignment]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        return form
