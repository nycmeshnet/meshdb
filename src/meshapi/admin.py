from django.contrib import admin
from django.contrib.admin.options import forms

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"


# This controls the list of installs reverse FK'd to Buildings and Members
class InstallInline(admin.TabularInline):
    model = Install
    extra = 0
    fields = ["status", "node", "member", "unit"]
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }

class FromLinkInline(admin.TabularInline):
    model = Link
    extra = 0
    fields = ["type", "status", "from_device", "to_device"]
    fk_name = "from_device"
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request, obj):
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }

class ToLinkInline(admin.TabularInline):
    model = Link
    extra = 0
    fields = ["type", "status", "from_device", "to_device"]
    fk_name = "to_device"
    readonly_fields = fields
    can_delete = False
    template = "admin/install_tabular.html"

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
            "Node Details",
            {
                "fields": [
                    "primary_node",
                    "nodes",
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
    inlines = [InstallInline]
    filter_horizontal = ('nodes',)


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
                    "member",
                    "status",
                    "ticket_id",
                    "node",
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
        "from_device__node__name__icontains",
        "to_device__node__name__icontains",
        "from_device__node__buildings__street_address__icontains",
        "to_device__node__buildings__street_address__icontains",
        "from_device__node__network_number__iexact",
        "to_device__node__network_number__iexact",
    ]
    list_display = ["__str__", "status", "from_device", "to_device", "description"]
    list_filter = ["status", "type"]


#class SectorAdminForm(forms.ModelForm):
#    class Meta:
#        model = Link
#        fields = "__all__"
#        widgets = {
#            "name": forms.TextInput(),
#            "model": forms.TextInput(),
#            "ssid": forms.TextInput(),
#        }
#
#
#@admin.register(Sector)
#class SectorAdmin(admin.ModelAdmin):
#    form = SectorAdminForm
#    search_fields = ["name__icontains", "model__icontains", "ssid__icontains"]
#    list_display = [
#        "__str__",
#        "ssid",
#        "name",
#        "model",
#    ]
#    list_filter = ["model", "install_date"]


class NodeAdminForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = "__all__"


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    form = NodeAdminForm
    search_fields = ["network_number__iexact", "name__icontains"]
    list_filter = ["status", ("name", admin.EmptyFieldListFilter)]
    list_display = ["__network_number__", "name", "status"] 


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
    list_filter = ["status", "install_date", "model",]
    inlines = [ToLinkInline, FromLinkInline]
    
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
    list_filter = ["status", "install_date", "model",]
    inlines = [ToLinkInline, FromLinkInline]
    
