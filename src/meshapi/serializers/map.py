import datetime
import os
from collections import OrderedDict
from typing import List, Optional
from urllib.parse import urlparse

from rest_framework import serializers

from meshapi.models import Install, Link, Node, Sector

EXCLUDED_INSTALL_STATUSES = {
    Install.InstallStatus.CLOSED,
    Install.InstallStatus.NN_REASSIGNED,
}
ALLOWED_INSTALL_STATUSES = set(Install.InstallStatus.values) - EXCLUDED_INSTALL_STATUSES


class JavascriptDateField(serializers.IntegerField):
    def to_internal_value(self, date_int_val: int) -> Optional[datetime.date]:
        if date_int_val is None:
            return None

        return datetime.datetime.fromtimestamp(date_int_val / 1000).date()

    def to_representation(self, date_val: datetime.date) -> Optional[int]:
        if date_val is None:
            return None

        return int(
            datetime.datetime.combine(
                date_val,
                datetime.datetime.min.time(),
            ).timestamp()
            * 1000
        )


class MapDataInstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = (
            "id",
            "name",
            "status",
            "coordinates",
            "requestDate",
            "installDate",
            "roofAccess",
            "notes",
            "panoramas",
        )

    id = serializers.IntegerField(source="install_number")
    name = serializers.SerializerMethodField("get_node_name")
    status = serializers.SerializerMethodField("convert_status_to_spreadsheet_status")
    coordinates = serializers.SerializerMethodField("get_building_coordinates")
    requestDate = JavascriptDateField(source="request_date")
    installDate = JavascriptDateField(source="install_date")
    roofAccess = serializers.BooleanField(source="roof_access")
    notes = serializers.SerializerMethodField("get_synthetic_notes")
    panoramas = serializers.SerializerMethodField("get_panorama_filename")

    def get_building_coordinates(self, install: Install) -> List[float]:
        building = install.building
        return [building.longitude, building.latitude, building.altitude]

    def get_node_name(self, install: Install) -> Optional[str]:
        # Only include the node name if this is an old-school "node as install" situation
        # to prevent showing the same name on multiple map dots. For the NN != install number
        # case we add extra fake install objects with install_number = NN so that we can still
        # see the node name
        node = install.node
        return node.name if node and install.node.network_number == install.install_number else None

    def get_synthetic_notes(self, install: Install) -> Optional[str]:
        if not install.node:
            return None

        # Start the notes with the map display type
        synthetic_notes = []

        if install.node.type != Node.NodeType.STANDARD:
            synthetic_notes.append(install.node.type)

        # Supplement with "Omni" if this node has an omni attached
        for device in install.node.devices.all():
            if "omni" in device.model.lower():
                synthetic_notes.append("Omni")

        return " ".join(synthetic_notes) if synthetic_notes else None

    def convert_status_to_spreadsheet_status(self, install: Install) -> Optional[str]:
        if install.status == Install.InstallStatus.REQUEST_RECEIVED:
            return None
        elif install.status == Install.InstallStatus.PENDING:
            return "Interested"
        elif install.status == Install.InstallStatus.BLOCKED:
            return "No Los"
        elif install.status == Install.InstallStatus.ACTIVE:
            return "Installed"
        elif install.status == Install.InstallStatus.INACTIVE:
            return "Powered Off"
        elif install.status == Install.InstallStatus.CLOSED:
            return "Abandoned"
        elif install.status == Install.InstallStatus.NN_REASSIGNED:
            return "NN assigned"

        return install.status

    # We're storing full URLs for each pano to make the system more flexible, so to
    # make it "map friendly", we gotta strip it down to just the filename.
    def get_panorama_filename(self, install):
        pano_filenames = []
        for panorama in install.building.panoramas:
            pano_url = urlparse(panorama)
            pano_filenames.append(os.path.basename(pano_url.path))
        return pano_filenames

    def to_representation(self, install):
        result = super().to_representation(install)

        # Remove null fields when applicable to match the existing interface
        for key in ["name", "status", "notes", "installDate"]:
            if result[key] is None:
                del result[key]

        return result


class MapDataLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = (
            "from_",
            "to",
            "status",
            "installDate",
        )

    from_ = serializers.SerializerMethodField("get_from_node_number")
    to = serializers.SerializerMethodField("get_to_node_number")
    status = serializers.SerializerMethodField("convert_status_to_spreadsheet_status")
    installDate = JavascriptDateField(source="install_date")

    def convert_status_to_spreadsheet_status(self, link: Link) -> str:
        if link.status != Link.LinkStatus.ACTIVE:
            return str(link.status).lower()

        if link.type == Link.LinkType.FIBER:
            return "fiber"
        elif link.type == Link.LinkType.VPN:
            return "vpn"
        elif link.type == Link.LinkType.MMWAVE:
            return "60GHz"

        return "active"

    def get_to_node_number(self, link: Link) -> int:
        return link.to_device.node.network_number

    def get_from_node_number(self, link: Link) -> int:
        return link.from_device.node.network_number

    def get_fields(self) -> dict:
        result = super().get_fields()
        # Rename `from_` to `from`
        from_ = result.pop("from_")

        new_fields = OrderedDict({"from": from_})
        for key, value in result.items():
            new_fields[key] = value

        return new_fields

    def to_representation(self, link: Link) -> dict:
        result = super().to_representation(link)

        # Remove null fields when applicable to match the existing interface
        for key in ["installDate"]:
            if result[key] is None:
                del result[key]

        return result


class MapDataSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = (
            "nodeId",
            "radius",
            "azimuth",
            "width",
            "status",
            "device",
            "installDate",
        )

    nodeId = serializers.SerializerMethodField("get_node_id")
    status = serializers.SerializerMethodField("convert_status_to_spreadsheet_status")
    device = serializers.CharField(source="model")
    installDate = JavascriptDateField(source="install_date")

    def get_node_id(self, sector: Sector) -> int:
        return sector.node.network_number

    def convert_status_to_spreadsheet_status(self, sector: Sector) -> str:
        return str(sector.status).lower()

    def to_representation(self, sector: Sector) -> dict:
        result = super().to_representation(sector)

        # Remove null fields when applicable to match the existing interface
        for key in ["installDate"]:
            if result[key] is None:
                del result[key]

        return result
