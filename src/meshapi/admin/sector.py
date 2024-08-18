from django.contrib import admin
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
    search_fields = ["name__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "name",
    ]
    list_filter = [
        "status",
        "install_date",
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
