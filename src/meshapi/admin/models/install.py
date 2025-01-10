import os
from typing import Any, Tuple

import tablib
from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.http import HttpRequest
from import_export import resources
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import Install
from meshapi.widgets import ExternalHyperlinkWidget, InstallStatusWidget

from ..ranked_search import RankedSearchMixin

OSTICKET_URL = os.environ.get("OSTICKET_URL", "https://support.nycmesh.net")


class InstallImportExportResource(resources.ModelResource):
    def before_import(self, dataset: tablib.Dataset, **kwargs: Any) -> None:
        if "install_number" not in dataset.headers:
            dataset.headers.append("install_number")
        super().before_import(dataset, **kwargs)

    class Meta:
        model = Install
        import_id_fields = ("install_number",)


class InstallAdminForm(forms.ModelForm):
    class Meta:
        model = Install
        fields = "__all__"
        widgets = {
            "unit": forms.TextInput(),
            "ticket_number": ExternalHyperlinkWidget(
                lambda ticket_number: f"{OSTICKET_URL}/scp/tickets.php?number={ticket_number}",
                title="View in OSTicket",
            ),
            "status": InstallStatusWidget(),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.form_instance = self


@admin.register(Install)
class InstallAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = InstallAdminForm
    resource_classes = [InstallImportExportResource]
    list_filter = [
        ("node", admin.EmptyFieldListFilter),
        "status",
        "request_date",
        "install_date",
        "abandon_date",
    ]
    list_display = ["__str__", "status", "node", "member", "building", "unit"]
    list_select_related = ["node", "member", "building"]
    search_fields = [
        # Install number
        "install_number__iexact",
        "node__network_number__iexact",
        "ticket_number__iexact",
        # Search by building details
        "building__street_address__icontains",
        "unit__icontains",
        "building__zip_code__iexact",
        "building__bin__iexact",
        # Search by member details
        "member__name__icontains",
        "member__primary_email_address__icontains",
        "member__phone_number__iexact",
        "member__slack_handle__iexact",
        # Notes
        "@referral",
        "@notes",
    ]
    search_vector = (
        SearchVector("install_number", weight="A")
        + SearchVector("node__network_number", weight="A")
        + SearchVector("member__name", weight="A")
        + SearchVector("member__primary_email_address", weight="B")
        + SearchVector("member__phone_number", weight="B")
        + SearchVector("member__slack_handle", weight="C")
        + SearchVector("building__street_address", weight="C")
        + SearchVector("unit", weight="C")
        + SearchVector("building__zip_code", weight="C")
        + SearchVector("building__bin", weight="C")
        + SearchVector("ticket_number", weight="C")
        + SearchVector("referral", weight="D")
        + SearchVector("notes", weight="D")
    )
    autocomplete_fields = ["building", "member"]
    readonly_fields = ["install_number"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "install_number",
                    "status",
                    "ticket_number",
                    "member",
                ]
            },
        ),
        (
            "Node",
            {
                "fields": [
                    "node",
                ]
            },
        ),
        (
            "Building",
            {
                "fields": [
                    "building",
                    "unit",
                    "roof_access",
                ]
            },
        ),
        (
            "Dates",
            {
                "fields": [
                    "request_date",
                    "install_date",
                    "abandon_date",
                ],
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "diy",
                    "referral",
                    "notes",
                ]
            },
        ),
    ]

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet[Install], search_term: str
    ) -> Tuple[QuerySet[Install], bool]:
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            upper_search = search_term.upper()
            if len(upper_search) > 2 and upper_search[:2] == "NN":
                search_term_as_int = int(upper_search[2:])
                queryset = (
                    self.rank_queryset(
                        self.model.objects.filter(node__network_number=search_term_as_int),
                        upper_search[2:],
                    )
                    | queryset  # We do this rather than |= since it floats the more relevant results to the top
                )
                may_have_duplicates = False
        except ValueError:
            pass
        return queryset, may_have_duplicates
