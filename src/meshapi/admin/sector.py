from django.contrib import admin
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.device import UISP_URL, DeviceAdmin, DeviceAdminForm
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Sector
from meshapi.widgets import ExternalHyperlinkWidget


class SectorAdminForm(DeviceAdminForm):
    class Meta:
        model = Sector
        fields = "__all__"
        widgets = {
            "uisp_id": ExternalHyperlinkWidget(
                lambda uisp_id: f"{UISP_URL}/devices#id={uisp_id}&panelType=device-panel",
                title="View in UISP",
            ),
        }


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
