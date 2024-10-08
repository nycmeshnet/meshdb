import os
from typing import Optional

from django import forms
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import Device
from meshapi.widgets import ExternalHyperlinkWidget

from ..inlines import DeviceLinkInline
from ..ranked_search import RankedSearchMixin
from ..utils import downclass_device, get_admin_url

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
class DeviceAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
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

    def _get_subtype_redirect(self, request: HttpRequest, object_id: str) -> Optional[HttpResponseRedirect]:
        """Create a redirect for an AP or sector device by its object ID (if such a subtype exists)"""
        device = Device.objects.filter(pk=object_id).first()
        if not device:
            return None

        downclassed_model_obj = downclass_device(device)
        target_url = get_admin_url(downclassed_model_obj, site_base_url=f"{request.scheme}://{request.get_host()}")
        return redirect(target_url)

    def _changeform_view(
        self, request: HttpRequest, object_id: str, form_url: str, extra_context: dict
    ) -> HttpResponse:
        if object_id and not self.get_object(request, unquote(object_id), None):
            # If the built-in object lookup logic doesn't find this device,
            # it's probably because it's excluded in get_queryset() above
            # (as a Sector or AP). However, there are some direct links to device objects,
            # and if the user has hit one of those, we try to redirect them to the more
            # specific page so they don't get 404ed
            redirect = self._get_subtype_redirect(request, object_id)
            if redirect:
                return redirect

        return super()._changeform_view(request, object_id, form_url, extra_context)
