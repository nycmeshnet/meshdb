from django import forms
from django.contrib import admin

from meshapi.models import LOS


class LOSAdminForm(forms.ModelForm):
    class Meta:
        model = LOS
        fields = "__all__"


@admin.register(LOS)
class LOSAdmin(admin.ModelAdmin):
    form = LOSAdminForm
    search_fields = [
        "from_building__primary_node__name__icontains",
        "to_building__primary_node__name__icontains",
        "from_building__street_address__icontains",
        "to__building__street_address__icontains",
        "from_building__primary_node__network_number__iexact",
        "to_building__primary_node__network_number__iexact",
        "notes__icontains",
    ]
    list_display = ["__str__", "source", "from_building", "to_building", "analysis_date"]
    list_filter = ["source"]

    autocomplete_fields = ["from_building", "to_building"]
