from typing import Any, Optional

from django.contrib import admin
from django.db.models import Model, Q, QuerySet
from django.http import HttpRequest
from nonrelated_inlines.admin import NonrelatedTabularInline

from meshapi.models import Building, Device, Install, Link, Node, Sector


# Inline with the typical rules we want + Formatting
class BetterInline(admin.TabularInline):
    extra = 0
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request: HttpRequest, obj: Optional[Any]) -> bool:  # type: ignore[override]
        return False

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


class BetterNonrelatedInline(NonrelatedTabularInline):
    extra = 0
    can_delete = False
    template = "admin/install_tabular.html"

    def has_add_permission(self, request: HttpRequest, obj: Model) -> bool:
        return False

    def save_new_instance(self, parent: Any, instance: Any) -> None:
        pass

    class Media:
        css = {
            "all": ("admin/install_tabular.css",),
        }


# This is such a horrific hack but it works I guess?
class PanoramaInline(BetterNonrelatedInline):
    model = Building
    fields = ["panoramas"]
    readonly_fields = fields
    template = "admin/node_panorama_viewer.html"

    all_panoramas: dict[str, list[Any]] = {}

    def get_form_queryset(self, obj: Node) -> QuerySet[Building]:
        buildings = self.model.objects.filter(nodes=obj)
        panoramas = []
        for b in buildings:
            panoramas += b.panoramas
        self.all_panoramas = {"value": panoramas}
        return buildings

    class Media:
        css = {
            "all": ("widgets/panorama_viewer.css", "widgets/flickity.min.css"),
        }
        js = ["widgets/flickity.pkgd.min.js"]


class NonrelatedBuildingInline(BetterNonrelatedInline):
    model = Building
    fields = ["primary_node", "bin", "street_address", "city", "zip_code"]
    readonly_fields = fields

    add_button = True

    # Hack to get the NN
    network_number = None

    def get_form_queryset(self, obj: Node) -> QuerySet[Building]:
        self.network_number = obj.pk
        return self.model.objects.filter(nodes=obj)


class BuildingMembershipInline(admin.TabularInline):
    model = Building.nodes.through
    extra = 0
    autocomplete_fields = ["building_id"]
    classes = ["collapse"]
    verbose_name = "Building"
    verbose_name_plural = "Edit Related Buildings"


class DeviceInline(BetterInline):
    model = Device
    fields = ["status", "type", "model"]
    readonly_fields = fields  # type: ignore[assignment]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Device]:
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset


class NodeLinkInline(BetterNonrelatedInline):
    model = Link
    fields = ["status", "type", "from_device", "to_device"]
    readonly_fields = fields

    def get_form_queryset(self, obj: Node) -> QuerySet[Link]:
        from_device_q = Q(from_device__in=obj.devices.all())
        to_device_q = Q(to_device__in=obj.devices.all())
        all_links = from_device_q | to_device_q
        return self.model.objects.filter(all_links)


class DeviceLinkInline(BetterNonrelatedInline):
    model = Link
    fields = ["status", "type", "from_device", "to_device"]
    readonly_fields = fields

    def get_form_queryset(self, obj: Link) -> QuerySet[Link]:
        from_device_q = Q(from_device=obj)
        to_device_q = Q(to_device=obj)
        all_links = from_device_q | to_device_q
        return self.model.objects.filter(all_links)


class SectorInline(BetterInline):
    model = Sector
    fields = ["status", "type", "model"]
    readonly_fields = fields  # type: ignore[assignment]


# This controls the list of installs reverse FK'd to Buildings and Members
class InstallInline(BetterInline):
    model = Install
    fields = ["status", "node", "member", "building", "unit"]
    readonly_fields = fields  # type: ignore[assignment]
