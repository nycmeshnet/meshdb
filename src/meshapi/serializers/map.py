import datetime
import os
from collections import OrderedDict
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from meshapi.models import Device, Install, Link, Node, Sector

EXCLUDED_INSTALL_STATUSES = {
    Install.InstallStatus.CLOSED,
    Install.InstallStatus.NN_REASSIGNED,
}
ALLOWED_INSTALL_STATUSES = set(Install.InstallStatus.values) - EXCLUDED_INSTALL_STATUSES


@extend_schema_field(OpenApiTypes.INT)
class JavascriptDateField(serializers.Field):
    def to_internal_value(self, date_int_val: Optional[int]) -> Optional[datetime.date]:
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
    coordinates = serializers.SerializerMethodField("get_coordinates")
    requestDate = JavascriptDateField(source="request_date")
    installDate = JavascriptDateField(source="install_date")
    roofAccess = serializers.BooleanField(source="roof_access")
    notes = serializers.SerializerMethodField("get_synthetic_notes")
    panoramas = serializers.SerializerMethodField("get_panorama_filename")

    def get_coordinates(self, install: Install) -> Tuple[float, float, Optional[float]]:
        if install.node and (install.status == Install.InstallStatus.NN_REASSIGNED or self._is_node_dot(install)):
            return install.node.longitude, install.node.latitude, install.node.altitude
        else:
            return install.building.longitude, install.building.latitude, install.building.altitude

    def _is_node_dot(self, install: Install) -> bool:
        # Check if this is an old-school "node as install" situation to prevent showing multiple
        # "node" map dots. For the NN != install number
        # case we add extra fake install objects with install_number = NN so that we can still
        # see the node name
        #
        # We also include the minimum install number associated with a Node without a network number
        # here so that we can show these as nodes
        node = install.node

        if not node:
            return False

        if not node.network_number:
            if install.install_number == min(inst.install_number for inst in node.installs.all()):
                return True
            else:
                return False

        if node.network_number == install.install_number:
            return True

        return False

    def get_node_name(self, install: Install) -> Optional[str]:
        if not install.node or not self._is_node_dot(install):
            return None

        return install.node.name

    def get_synthetic_notes(self, install: Install) -> Optional[str]:
        if not install.node:
            return None

        # Start the notes with the map display type
        synthetic_notes = []

        # In the case of multiple dots per node, we only want to
        # make the one that actually corresponds to the NN the big dot (the "fake" install)
        # for the real install numbers that don't match the network number, leave them as red dots
        if install.node.type != Node.NodeType.STANDARD and self._is_node_dot(install):
            synthetic_notes.append(install.node.type)

        # Supplement with "Omni" if this node has an omni attached
        for device in install.node.devices.all():
            if device.name and "omni" in device.name.lower():
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
    def get_panorama_filename(self, install: Install) -> List[str]:
        pano_filenames = []
        for panorama in install.building.panoramas:
            pano_url = urlparse(panorama)
            pano_filenames.append(os.path.basename(pano_url.path))
        return pano_filenames

    def to_representation(self, install: Install) -> dict:
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
        elif link.type in [
            Link.LinkType.TWENTYFOUR_GHZ,
            Link.LinkType.SIXTY_GHZ,
            Link.LinkType.SEVENTY_EIGHTY_GHZ,
        ]:
            return "60GHz"

        return "active"

    def _get_node_number_from_device(self, device: Device) -> Optional[int]:
        node = device.node

        if node.network_number:
            return node.network_number

        if node.installs.count():
            return min(install.install_number for install in node.installs.all())

        return None

    def get_to_node_number(self, link: Link) -> Optional[int]:
        return self._get_node_number_from_device(link.to_device)

    def get_from_node_number(self, link: Link) -> Optional[int]:
        return self._get_node_number_from_device(link.from_device)

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
            "installDate",
        )

    nodeId = serializers.SerializerMethodField("get_node_id")
    status = serializers.SerializerMethodField("convert_status_to_spreadsheet_status")
    installDate = JavascriptDateField(source="install_date")

    def get_node_id(self, sector: Sector) -> Optional[int]:
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
