from django.contrib import admin
from django.contrib.admin.options import forms
from meshapi.models import Building, Member, Install, Link, Sector

from django.shortcuts import resolve_url
from django.contrib.admin.templatetags.admin_urls import admin_urlname

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"

# Register your models here.


class BuildingAdminForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = "__all__"
        widgets = {
            "street_address": forms.TextInput(),
            "city": forms.TextInput(),
            "state": forms.TextInput(),
            "zip_code": forms.NumberInput(),
            "node_name": forms.TextInput(),
            "street_address": forms.TextInput(),
        }


class BoroughFilter(admin.SimpleListFilter):
    title = "Borough"
    parameter_name = "borough"

    def lookups(self, request, model_admin):
        return (
            ("bronx", ("The Bronx")),
            ("manhattan", ("Manhattan")),
            ("brooklyn", ("Brooklyn")),
            ("queens", ("Queens")),
            ("staten_island", ("Staten Island")),
        )

    def queryset(self, request, queryset):
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


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    form = BuildingAdminForm
    search_fields = [
        "street_address__icontains",
        "city__icontains",
        "node_name__icontains",
        "zip_code__iexact",
        "primary_nn__iexact",
        "bin__iexact",
    ]
    list_filter = ["building_status", ("primary_nn", admin.EmptyFieldListFilter), BoroughFilter]
    list_display = ["street_address", "node_name", "primary_nn"]
    fieldsets = [
        (
            "Node Details",
            {
                "fields": [
                    "node_name",
                    "primary_nn",
                    "building_status",
                ]
            },
        ),
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
            "Notes",
            {
                "fields": [
                    "notes",
                ]
            },
        ),
    ]


class MemberAdminForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = "__all__"
        exclude = ["invalid"]
        widgets = {
            "name": forms.TextInput(),
            "phone_number": forms.TextInput(),
            "slack_handle": forms.TextInput(),
        }


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    form = MemberAdminForm
    search_fields = ["name__icontains"]
    list_display = ["name", "email_address", "phone_number"]


class InstallAdminForm(forms.ModelForm):
    class Meta:
        model = Install
        fields = "__all__"
        widgets = {
            "unit": forms.TextInput(),
        }


@admin.register(Install)
class InstallAdmin(admin.ModelAdmin):
    form = InstallAdminForm
    list_filter = ["install_status"]
    list_display = ["install_number", "network_number", "member", "building"]
    search_fields = ["install_number__icontains"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "member",
                    "install_status",
                    # "install_number",
                    "ticket_id",
                    "network_number",
                ]
            },
        ),
        (
            "Building Details",
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
            "Notes",
            {
                "fields": [
                    "notes",
                    "referral",
                ]
            },
        ),
    ]


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    pass


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    pass
