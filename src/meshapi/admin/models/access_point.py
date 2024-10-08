from typing import Any, Optional, Type

from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from django.forms import Field, ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import AccessPoint
from meshapi.widgets import AutoPopulateLocationWidget, DeviceIPAddressWidget, ExternalHyperlinkWidget

from ..ranked_search import RankedSearchMixin
from .device import UISP_URL, DeviceAdmin, DeviceAdminForm, DeviceLinkInline


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
            "uisp_id": ExternalHyperlinkWidget(
                lambda uisp_id: f"{UISP_URL}/devices#id={uisp_id}&panelType=device-panel",
                title="View in UISP",
            ),
        }


@admin.register(AccessPoint)
class AccessPointAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = AccessPointAdminForm
    search_fields = ["name__icontains", "@notes"]
    search_vector = SearchVector("name", weight="A") + SearchVector("notes", weight="D")
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
