import os

from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.models import Device
from meshapi.widgets import ExternalHyperlinkWidget

from ..inlines import DeviceLinkInline
from ..ranked_search import RankedSearchMixin

UISP_URL = os.environ.get("UISP_URL", "https://uisp.mesh.nycmesh.net/nms")


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"
        readonly_fields = ["uisp_link"]
        widgets = {
            "uisp_id": ExternalHyperlinkWidget(
                lambda uisp_id: f"{UISP_URL}/devices#id={uisp_id}&panelType=device-panel",
                title="View in UISP",
            ),
        }


@admin.register(Device)
class DeviceAdmin(RankedSearchMixin, ImportExportModelAdmin, ExportActionMixin):
    form = DeviceAdminForm
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

        # If we are calling the search endpoint from the dropdown on the link model, don't exclude
        # anything, keep all the sectors and APs as options
        if not request.GET.get("model_name") == "link":
            # However, if we are on the main search/list page, exclude these other models since
            # they have their own pages for this
            queryset = queryset.exclude(sector__isnull=False).exclude(accesspoint__isnull=False)

        return queryset
