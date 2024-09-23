from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import Sector
from meshapi.widgets import ExternalHyperlinkWidget

from ..ranked_search import RankedSearchMixin
from .device import UISP_URL, DeviceAdmin, DeviceAdminForm, DeviceLinkInline


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
class SectorAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = SectorAdminForm
    search_fields = ["name__icontains", "@notes"]
    search_vector = SearchVector("name", weight="A") + SearchVector("notes", weight="D")
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
