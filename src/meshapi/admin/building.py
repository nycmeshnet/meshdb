from typing import Iterable

from django import forms
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from meshapi.admin.inlines import InstallInline
from meshapi.models import Building
from meshapi.widgets import PanoramaViewer


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
    class Meta:
        model = Building
        fields = "__all__"
        widgets = {
            "panoramas": PanoramaViewer(schema={"type": "array", "items": {"type": "string"}}),
            "bin": forms.NumberInput(attrs={"style": "width:21ch"}),
        }


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    form = BuildingAdminForm
    list_display = ["__str__", "street_address", "primary_node"]
    search_fields = [
        # Sometimes they have an actual name
        "nodes__name__icontains",
        # Address info
        "street_address__icontains",
        "city__icontains",
        "state__icontains",
        "zip_code__iexact",
        "bin__iexact",
        # Search by NN
        "nodes__network_number__iexact",
        "installs__install_number__iexact",
        # Search by Member info
        "installs__member__name__icontains",
        "installs__member__primary_email_address__icontains",
        "installs__member__phone_number__iexact",
        "installs__member__slack_handle__iexact",
        # Notes
        "notes__icontains",
    ]
    list_filter = [
        BoroughFilter,
        ("primary_node", admin.EmptyFieldListFilter),
    ]
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
            "NYC Information",
            {
                "fields": [
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
    inlines = [InstallInline]
    filter_horizontal = ("nodes",)
