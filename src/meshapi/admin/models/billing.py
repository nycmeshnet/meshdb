from typing import Any, OrderedDict

from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from import_export import resources
from import_export.admin import ExportActionMixin, ImportExportMixin
from pydantic import UUID4
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models.billing import InstallFeeBillingDatum

from ...models import Install
from ..ranked_search import RankedSearchMixin


class InstallFeeBillingDatumImportExportResource(resources.ModelResource):
    def before_import_row(self, row: OrderedDict, **kwargs: Any) -> None:
        if row.get("install") is not None:
            try:
                UUID4(row["install"])
            except ValueError:
                # If the "install" column is not a valid UUID, perhaps it is an install number
                install_obj = Install.objects.filter(install_number=row["install"]).first()
                if install_obj:
                    row["install"] = install_obj.id

        super().before_import_row(row, **kwargs)

    class Meta:
        model = InstallFeeBillingDatum


class InstallFeeBillingDatumAdminForm(forms.ModelForm):
    class Meta:
        model = InstallFeeBillingDatum
        fields = "__all__"


@admin.register(InstallFeeBillingDatum)
class InstallFeeBillingDatumAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = InstallFeeBillingDatumAdminForm
    resource_classes = [InstallFeeBillingDatumImportExportResource]
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
