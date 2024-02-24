from django.contrib import admin
from django.contrib.admin.options import forms
from django.db.models import Q, QuerySet

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector

from nonrelated_inlines.admin import NonrelatedTabularInline
from django.utils.safestring import mark_safe
from django_jsonform.widgets import JSONFormWidget

from meshapi.models import Building, Install, Link, Member, Sector
from meshapi.widgets import PanoramaViewer

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"


# Inline with the typical rules we want + Formatting
class BetterInline(admin.TabularInline):
    extra = 0
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


class BetterNonrelatedInline(NonrelatedTabularInline):
    extra = 0
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


class NonrelatedBuildingInline(BetterNonrelatedInline):
    model = Building
    fields = ["primary_node", "bin", "street_address", "city", "zip_code"]
    readonly_fields = fields

    def get_form_queryset(self, obj):
        return self.model.objects.filter(nodes=obj)

    def save_new_instance(self, parent, instance):
        pass


# This controls the list of installs reverse FK'd to Buildings and Members
class InstallInline(BetterInline):
    model = Install
    fields = ["status", "node", "member", "building", "unit"]
    readonly_fields = fields


class DeviceInline(BetterInline):
    model = Device
    fields = ["status", "type", "model"]
    readonly_fields = fields

    def get_queryset(self, request):
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset


class NodeLinkInline(BetterNonrelatedInline):
    model = Link
    fields = ["status", "type", "from_device", "to_device"]
    readonly_fields = fields

    def get_form_queryset(self, obj):
        from_device_q = Q(from_device__in=obj.devices.all())
        to_device_q = Q(to_device__in=obj.devices.all())
        all_links = from_device_q | to_device_q
        return self.model.objects.filter(all_links)

    def save_new_instance(self, parent, instance):
        pass


class DeviceLinkInline(BetterNonrelatedInline):
    model = Link
    fields = ["status", "type", "from_device", "to_device"]
    readonly_fields = fields

    def get_form_queryset(self, obj):
        from_device_q = Q(from_device=obj)
        to_device_q = Q(to_device=obj)
        all_links = from_device_q | to_device_q
        return self.model.objects.filter(all_links)

    def save_new_instance(self, parent, instance):
        pass


class SectorInline(BetterInline):
    model = Sector
    fields = ["status", "type", "model"]
    readonly_fields = fields


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
            "panoramas": PanoramaViewer(schema={"type": "array", "items": {"type": "string"}}),
        }


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
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
        "installs__node__network_number__iexact",
        "installs__install_number__iexact",
    ]
    list_display = [
        "__str__",
        "name",
        "primary_email_address",
        "stripe_email_address",
        "phone_number",
    ]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "name",
                ]
            },
        ),
        (
            "Email",
            {
                "fields": [
                    "primary_email_address",
                    "stripe_email_address",
                    "additional_email_addresses",
                ]
            },
        ),
        (
            "Contact Info",
            {
                "fields": [
                    "phone_number",
                    "slack_handle",
                ]
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "notes",
                ]
            },
        ),
    ]
    inlines = [InstallInline]


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
        ("node", admin.EmptyFieldListFilter),
        "status",
        "request_date",
        "install_date",
        "abandon_date",
    ]
    list_display = ["__str__", "status", "node", "member", "building", "unit"]
    search_fields = [
        # Install number
        "install_number__iexact",
        "node__network_number__iexact",
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
                    "status",
                    "ticket_id",
                    "member",
                ]
            },
        ),
        (
            "Node",
            {
                "fields": [
                    "node",
                ]
            },
        ),
        (
            "Building",
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
            "Misc",
            {
                "fields": [
                    "diy",
                    "referral",
                    "notes",
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
        "from_device__node__name__icontains",
        "to_device__node__name__icontains",
        "from_device__node__buildings__street_address__icontains",
        "to_device__node__buildings__street_address__icontains",
        "from_device__node__network_number__iexact",
        "to_device__node__network_number__iexact",
    ]
    list_display = ["__str__", "status", "from_device", "to_device", "description"]
    list_filter = ["status", "type"]

    autocomplete_fields = ["from_device", "to_device"]


class NodeAdminForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = "__all__"


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    form = NodeAdminForm
    search_fields = ["network_number__iexact", "name__icontains", "buildings__street_address__icontains"]
    list_filter = ["status", ("name", admin.EmptyFieldListFilter)]
    list_display = ["__network_number__", "name", "status", "address"]
    fieldsets = [
        (
            "Details",
            {
                "fields": [
                    "status",
                    "name",
                ]
            },
        ),
        (
            "Location",
            {
                "fields": [
                    "latitude",
                    "longitude",
                    "altitude",
                ]
            },
        ),
        (
            "Dates",
            {
                "fields": [
                    "install_date",
                    "abandon_date",
                ]
            },
        ),
        (
            "Misc",
            {
                "fields": [
                    "notes",
                ]
            },
        ),
    ]
    inlines = [InstallInline, NonrelatedBuildingInline, DeviceInline, SectorInline, NodeLinkInline]

    def address(self, obj):
        return obj.buildings.first()


device_fieldsets = [
    (
        "Details",
        {
            "fields": [
                "status",
                "name",
                "ssid",
                "node",
            ]
        },
    ),
    (
        "Location",
        {
            "fields": [
                "latitude",
                "longitude",
                "altitude",
            ]
        },
    ),
    (
        "Dates",
        {
            "fields": [
                "install_date",
                "abandon_date",
            ]
        },
    ),
    (
        "Misc",
        {
            "fields": [
                "model",
                "type",
                "uisp_id",
                "notes",
            ]
        },
    ),
]


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    search_fields = ["name__icontains", "model__icontains", "ssid__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "model",
    ]
    list_filter = [
        "status",
        "install_date",
        "model",
    ]
    fieldsets = device_fieldsets
    inlines = [DeviceLinkInline]

    def get_queryset(self, request):
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset


class SectorAdminForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = "__all__"


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    form = SectorAdminForm
    search_fields = ["name__icontains", "model__icontains", "ssid__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "model",
    ]
    list_filter = [
        "status",
        "install_date",
        "model",
    ]
    inlines = [DeviceLinkInline]
    fieldsets = device_fieldsets + [
        (
            "Sector Attributes",
            {
                "fields": [
                    "radius",
                    "azimuth",
                    "width",
                ]
            },
        ),
    ]
