import datetime
from typing import Optional

from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.models import LOS


class LOSAdminForm(forms.ModelForm):
    class Meta:
        model = LOS
        fields = "__all__"


@admin.register(LOS)
class LOSAdmin(ImportExportModelAdmin, ExportActionMixin):
    form = LOSAdminForm
    search_fields = [
        "from_building__primary_node__name__icontains",
        "to_building__primary_node__name__icontains",
        "from_building__street_address__icontains",
        "to_building__street_address__icontains",
        "from_building__primary_node__network_number__iexact",
        "to_building__primary_node__network_number__iexact",
        "notes__icontains",
    ]
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
