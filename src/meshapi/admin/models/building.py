from typing import Any, Iterable, Optional, Type

from django import forms
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from meshapi.models import Building
from meshapi.widgets import AutoPopulateLocationWidget, PanoramaViewer

from ..inlines import BuildingLOSInline, InstallInline
from ..ranked_search import RankedSearchMixin


class BoroughFilter(admin.SimpleListFilter):
    title = "Borough"
    parameter_name = "borough"

    def lookups(self, request: HttpRequest, model_admin: ModelAdmin) -> Iterable[tuple[str, str]]:
        return [
            ("bronx", "The Bronx"),
            ("manhattan", "Manhattan"),
            ("brooklyn", "Brooklyn"),
            ("queens", "Queens"),
            ("staten_island", "Staten Island"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Building]) -> QuerySet[Building]:
        if self.value() == "bronx":
            return queryset.filter(city="Bronx")
        elif self.value() == "manhattan":
            return queryset.filter(city="New York")
        elif self.value() == "brooklyn":
            return queryset.filter(city="Brooklyn")
        elif self.value() == "queens":
            return queryset.filter(city="Queens")
        elif self.value() == "staten_island":
            return queryset.filter(city="Staten Island")
        return queryset


class BuildingAdminForm(forms.ModelForm):
    auto_populate_location_field = forms.Field(
        required=False,
        widget=AutoPopulateLocationWidget("Address"),
    )

    class Meta:
        model = Building
        fields = "__all__"
        widgets = {
            "panoramas": PanoramaViewer(schema={"type": "array", "items": {"type": "string"}}),
            "bin": forms.NumberInput(attrs={"style": "width:21ch"}),
        }


@admin.register(Building)
class BuildingAdmin(RankedSearchMixin, ImportExportModelAdmin, ExportActionMixin):
    form = BuildingAdminForm
    list_display = ["__str__", "street_address", "primary_node"]
    search_fields = [
        # Sometimes they have an actual name
        "nodes__name__icontains",
        # Address info
        "street_address__icontains",
        "zip_code__iexact",
        "bin__iexact",
        # Search by NN
        "nodes__network_number__iexact",
        "installs__install_number__iexact",
        # Notes
        "@notes",
    ]
    search_vector = (
        SearchVector("nodes__name", weight="A")
        + SearchVector("street_address", weight="A")
        + SearchVector("zip_code", weight="A")
        + SearchVector("bin", weight="A")
        + SearchVector("nodes__network_number", weight="B")
        + SearchVector("installs__install_number", weight="B")
        + SearchVector("notes", weight="D")
    )
    list_filter = [
        BoroughFilter,
        ("primary_node", admin.EmptyFieldListFilter),
    ]
    list_select_related = ["primary_node"]
    fieldsets = [
        (
            "Address Information",
            {
                "fields": [
                    "street_address",
                    "city",
                    "state",
                    "zip_code",
                ]
            },
        ),
        (
            "Coordinates & NYC BIN",
            {
                "fields": [
                    "auto_populate_location_field",
                    "bin",
                    "latitude",
                    "longitude",
                    "altitude",
                ]
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "notes",
                    "panoramas",
                ]
            },
        ),
        (
            "Nodes",
            {
                "fields": [
                    "primary_node",
                    "nodes",
                ]
            },
        ),
    ]
    inlines = [InstallInline, BuildingLOSInline]

    def get_form(
        self, request: HttpRequest, obj: Optional[Any] = None, change: bool = False, **kwargs: Any
    ) -> Type[ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["auto_populate_location_field"].label = ""
        return form

    filter_horizontal = ("nodes",)
