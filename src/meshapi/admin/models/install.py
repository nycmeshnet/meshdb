import os
from typing import Any, List, Optional, Tuple

import tablib
from django import forms
from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.http import HttpRequest
from import_export import resources
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.admin import InstallFeeBillingDatumInline, inlines
from meshapi.models import Install
from meshapi.widgets import ExternalHyperlinkWidget, InstallStatusWidget, WarnAboutDatesWidget

from ..ranked_search import RankedSearchMixin

OSTICKET_URL = os.environ.get("OSTICKET_URL", "https://support.nycmesh.net")
STRIPE_SUBSCRIPTIONS_URL = os.environ.get("STRIPE_SUBSCRIPTIONS_URL", "https://dashboard.stripe.com/subscriptions/")


class InstallImportExportResource(resources.ModelResource):
    def before_import(self, dataset: tablib.Dataset, **kwargs: Any) -> None:
        if "install_number" not in dataset.headers:
            dataset.headers.append("install_number")
        super().before_import(dataset, **kwargs)

    class Meta:
        model = Install
        import_id_fields = ("install_number",)


class InstallAdminForm(forms.ModelForm):
    validate_install_abandon_date_set_widget = forms.Field(
        required=False,
        widget=WarnAboutDatesWidget(),
    )

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
            "stripe_subscription_id": ExternalHyperlinkWidget(
                lambda subscription_id: STRIPE_SUBSCRIPTIONS_URL + subscription_id,
                title="View on Stripe.com",
            ),
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
    list_display = ["__str__", "status", "node", "get_node_status", "member", "building", "unit"]
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
                    "stripe_subscription_id",
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
                    "validate_install_abandon_date_set_widget",  # Hidden by widget CSS
                ]
            },
        ),
    ]
    inlines = [inlines.AdditionalMembersInline]

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

    def get_node_status(self, obj: Install) -> str:
        if not obj.node or not obj.node.status:
            return "-"
        return obj.node.status

    def get_inline_instances(self, request: HttpRequest, obj: Optional[Install] = None) -> List[InlineModelAdmin]:
        static_inlines = super().get_inline_instances(request, obj)

        if (
            obj
            and hasattr(obj, "install_fee_billing_datum")
            and request.user.has_perm("meshapi.view_installfeebillingdatum", None)
        ):
            return static_inlines + [InstallFeeBillingDatumInline(self.model, self.admin_site)]

        return static_inlines  # Hide billing inline if no related objects exist

    get_node_status.short_description = "Node Status"  # type: ignore[attr-defined]
    get_node_status.admin_order_field = "node__status"  # type: ignore[attr-defined]
