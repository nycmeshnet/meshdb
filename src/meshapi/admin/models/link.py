from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from import_export.admin import ExportActionMixin, ImportExportMixin
from simple_history.admin import SimpleHistoryAdmin

from meshapi.models import Link

from ..ranked_search import RankedSearchMixin


class LinkAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = "__all__"
        widgets = {
            "description": forms.TextInput(),
        }


@admin.register(Link)
class LinkAdmin(RankedSearchMixin, ImportExportMixin, ExportActionMixin, SimpleHistoryAdmin):
    form = LinkAdminForm
    search_fields = [
        "from_device__node__name__icontains",
        "to_device__node__name__icontains",
        "from_device__node__buildings__street_address__icontains",
        "to_device__node__buildings__street_address__icontains",
        "from_device__node__network_number__iexact",
        "to_device__node__network_number__iexact",
        "@notes",
    ]
    search_vector = (
        SearchVector("from_device__node__network_number", weight="A")
        + SearchVector("to_device__node__network_number", weight="A")
        + SearchVector("from_device__node__name", weight="B")
        + SearchVector("to_device__node__name", weight="B")
        + SearchVector("from_device__node__buildings__street_address", weight="C")
        + SearchVector("to_device__node__buildings__street_address", weight="C")
        + SearchVector("notes", weight="D")
    )
    list_display = ["__str__", "status", "from_device", "to_device", "description"]
    list_filter = ["status", "type"]

    autocomplete_fields = ["from_device", "to_device"]
