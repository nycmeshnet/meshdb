import datetime
from typing import Optional

from django import forms
from django.contrib import admin
from django.contrib.postgres.search import SearchVector
from django.forms import ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.models import LOS

from ..ranked_search import RankedSearchMixin


class LOSAdminForm(forms.ModelForm):
    class Meta:
        model = LOS
        fields = "__all__"


@admin.register(LOS)
class LOSAdmin(RankedSearchMixin, ImportExportModelAdmin, ExportActionMixin):
    form = LOSAdminForm
    search_fields = [
        "from_building__nodes__network_number__iexact",
        "to_building__nodes__network_number__iexact",
        "from_building__installs__install_number__iexact",
        "to_building__installs__install_number__iexact",
        "from_building__nodes__name__icontains",
        "to_building__nodes__name__icontains",
        "from_building__street_address__icontains",
        "to_building__street_address__icontains",
        "@notes",
    ]
    search_vector = (
        SearchVector("from_building__nodes__network_number", weight="A")
        + SearchVector("to_building__nodes__network_number", weight="A")
        + SearchVector("from_building__installs__install_number", weight="A")
        + SearchVector("to_building__installs__install_number", weight="A")
        + SearchVector("from_building__nodes__name", weight="B")
        + SearchVector("to_building__nodes__name", weight="B")
        + SearchVector("from_building__street_address", weight="B")
        + SearchVector("to_building__street_address", weight="B")
        + SearchVector("notes", weight="D")
    )
    list_display = ["__str__", "source", "from_building", "to_building", "analysis_date"]
    list_filter = ["source"]

    autocomplete_fields = ["from_building", "to_building"]

    def get_form(
        self,
        request: HttpRequest,
        obj: Optional[LOS] = None,
        change: bool = False,
        **kwargs: dict,
    ) -> type[ModelForm]:
        form = super().get_form(request, obj, change, **kwargs)
        if not obj:
            # Autofill the form with today's date, unless we're editing
            # an existing object (so we don't accidentally mutate something)
            form.base_fields["analysis_date"].initial = datetime.date.today().isoformat()

        return form
