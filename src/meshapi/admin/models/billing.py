from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models.billing import InstallFeeBillingDatum

from ..ranked_search import RankedSearchMixin


class InstallFeeBillingDatumAdminForm(forms.ModelForm):
    class Meta:
        model = InstallFeeBillingDatum
        fields = "__all__"


@admin.register(InstallFeeBillingDatum)
class InstallFeeBillingDatumAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = InstallFeeBillingDatumAdminForm
    search_fields = [
        "invoice_number__iexact",
        # Also allow search by install, network number, street address, etc
        "install__node__network_number__iexact",
        "install__install_number__iexact",
        "install__building__street_address__icontains",
        "@notes",
    ]
    search_vector = (
        SearchVector("invoice_number", weight="A")
        + SearchVector("install__node__network_number", weight="A")
        + SearchVector("install__install_number", weight="A")
        + SearchVector("install__building__street_address", weight="B")
        + SearchVector("notes", weight="D")
    )
    list_display = ["__str__", "status", "billing_date", "invoice_number", "notes"]
    list_filter = ["status", "billing_date"]

    autocomplete_fields = ["install"]
