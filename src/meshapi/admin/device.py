import os

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Device
from meshapi.widgets import ExternalHyperlinkWidget, UISPHyperlinkWidget

UISP_URL = os.environ.get("UISP_URL", "https://uisp.mesh.nycmesh.net")


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"
        readonly_fields = ["uisp_link"]
        widgets = {
            "uisp_id": ExternalHyperlinkWidget(
                lambda uisp_id: f"{UISP_URL}/nms/devices#id={uisp_id}&panelType=device-panel",
                title="View in UISP",
            ),
        }


@admin.register(Device)
class DeviceAdmin(ImportExportModelAdmin, ExportActionMixin):
    form = DeviceAdminForm
    search_fields = ["name__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "name",
    ]
    list_filter = [
        "status",
        "install_date",
    ]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "status",
                    "name",
                    "node",
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
                    "uisp_id",
                    "notes",
                ]
            },
        ),
    ]
    inlines = [DeviceLinkInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Device]:
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False).exclude(accesspoint__isnull=False)
        return queryset
