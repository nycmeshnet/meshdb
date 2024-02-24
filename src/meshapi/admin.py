from django.contrib import admin
from django.contrib.admin.options import forms
from django.utils.safestring import mark_safe
from django_jsonform.widgets import JSONFormWidget

from meshapi.models import Building, Install, Link, Member, Sector

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"


# This controls the list of installs reverse FK'd to Buildings and Members
class InstallInline(admin.TabularInline):
    model = Install
    extra = 0
    fields = ["install_status", "network_number", "member", "unit"]
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


# This controls the list of installs reverse FK'd to Buildings and Members
class FromBuildingInline(admin.TabularInline):
    model = Link
    extra = 0
    # show_change_link = True
    fields = ["status", "to_building", "description"]
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"
    fk_name = "from_building"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


# This controls the list of installs reverse FK'd to Buildings and Members
class ToBuildingInline(admin.TabularInline):
    model = Link
    extra = 0
    # show_change_link = True
    fields = ["status", "from_building", "description"]
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"
    fk_name = "to_building"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
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
        }


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    form = BuildingAdminForm
    search_fields = [
        # Sometimes they have an actual name
        "node_name__icontains",
        # Address info
        "street_address__icontains",
        "city__icontains",
        "state__icontains",
        "zip_code__iexact",
        "bin__iexact",
        # Search by NN
        "primary_nn__iexact",
        "installs__network_number__iexact",
        "installs__install_number__iexact",
        # Search by Member info
        "installs__member__name__icontains",
        "installs__member__primary_email_address__icontains",
        "installs__member__phone_number__iexact",
        "installs__member__slack_handle__iexact",
    ]
    # inlines = [InstallInline, ToBuildingInline, FromBuildingInline]
    inlines = [InstallInline]
    list_filter = [
        "building_status",
        ("primary_nn", admin.EmptyFieldListFilter),
        ("node_name", admin.EmptyFieldListFilter),
        BoroughFilter,
    ]
    list_display = ["__str__", "street_address", "node_name", "primary_nn"]
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
                    "panoramas",
                ]
            },
        ),
    ]

    # This is probably a bad idea because you'll have to load a million panos
    # and OOM your computer
    # Need to find a way to "thumbnail-ize" them on the server side, probably.
    @mark_safe
    def thumb(self, obj):
        return f"<img src='{obj.get_thumb()}' width='50' height='50' />"

    thumb.__name__ = "Thumbnail"


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
    search_fields = [
        # Search by name
        "name__icontains",
        "primary_email_address__icontains",
        "stripe_email_address__icontains",
        "additional_email_addresses__icontains",
        "phone_number__icontains",
        "slack_handle__icontains",
        # Search by building details
        "installs__building__street_address__icontains",
        "installs__building__city__iexact",
        "installs__building__state__iexact",
        "installs__building__zip_code__iexact",
        "installs__building__bin__iexact",
        # Search by network number
        "installs__network_number__iexact",
        "installs__install_number__iexact",
    ]
    inlines = [InstallInline]
    list_display = [
        "__str__",
        "name",
        "primary_email_address",
        "stripe_email_address",
        "phone_number",
    ]


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
    list_filter = [
        ("network_number", admin.EmptyFieldListFilter),
        "install_status",
        "request_date",
        "install_date",
        "abandon_date",
    ]
    list_display = ["__str__", "install_status", "network_number", "member", "building", "unit"]
    search_fields = [
        # Install number
        "install_number__iexact",
        "network_number__iexact",
        # Search by building details
        "building__street_address__icontains",
        "building__city__iexact",
        "building__state__iexact",
        "building__zip_code__iexact",
        "building__bin__iexact",
        # Search by member details
        "member__name__icontains",
        "member__primary_email_address__icontains",
        "member__phone_number__iexact",
        "member__slack_handle__iexact",
    ]
    autocomplete_fields = ["building", "member"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "member",
                    "install_status",
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
                    "diy",
                    "notes",
                    "referral",
                ]
            },
        ),
    ]


class LinkAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = "__all__"
        widgets = {
            "description": forms.TextInput(),
        }


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    form = LinkAdminForm
    search_fields = [
        "from_building__node_name__icontains",
        "to_building__node_name__icontains",
        "from_building__street_address__icontains",
        "to_building__street_address__icontains",
        "from_building__primary_nn__iexact",
        "to_building__primary_nn__iexact",
    ]
    list_display = ["__str__", "status", "from_building", "to_building", "description"]
    list_filter = ["status", "type"]


class SectorAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(),
            "device_name": forms.TextInput(),
            "ssid": forms.TextInput(),
        }


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    form = SectorAdminForm
    search_fields = ["name__icontains", "device_name__icontains", "ssid__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "device_name",
    ]
    list_filter = ["device_name", "install_date"]
