import datetime
from collections import OrderedDict

from rest_framework import serializers

from meshapi.models import Install, Link, Sector

EXCLUDED_INSTALL_STATUSES = {
    Install.InstallStatus.CLOSED,
    Install.InstallStatus.NN_REASSIGNED,
}
ALLOWED_INSTALL_STATUSES = set(Install.InstallStatus.values) - EXCLUDED_INSTALL_STATUSES


class JavascriptDateField(serializers.IntegerField):
    def to_internal_value(self, date_int_val: int):
        if date_int_val is None:
            return None

        return datetime.datetime.fromtimestamp(date_int_val / 1000).date()

    def to_representation(self, date_val: datetime.date):
        if date_val is None:
            return None

        return int(
            datetime.datetime.combine(
                date_val,
                datetime.datetime.min.time(),
            ).timestamp()
            * 1000
        )


def get_install_number_from_node(node):
    installs = node.installs.exclude(status__in=EXCLUDED_INSTALL_STATUSES).order_by("install_number")
    active_installs = [install for install in installs if install.status == Install.InstallStatus.ACTIVE]
    if len(active_installs):
        return active_installs[0].install_number

    if len(installs):
        return installs.first().install_number
    else:
        return node.network_number


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
    notes = serializers.SerializerMethodField("get_start_of_notes")
    panoramas = serializers.ReadOnlyField(default=[])  # FIXME: THIS WILL REMOVE ALL PANORAMAS FROM THE MAP UI

    def get_building_coordinates(self, install):
        building = install.building
        return [building.longitude, building.latitude, building.altitude]

    def get_node_name(self, install):
        node = install.node
        return node.name if node else None

    def get_start_of_notes(self, install):
        if install.notes:
            note_parts = install.notes.split("\n")
            return note_parts[1] if len(note_parts) > 1 and note_parts[1] != "None" else None
        return None

    def convert_status_to_spreadsheet_status(self, install):
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
            return "NN Assigned"

        return install.status

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

    from_ = serializers.SerializerMethodField("get_from_install_number")
    to = serializers.SerializerMethodField("get_to_install_number")
    status = serializers.SerializerMethodField("convert_status_to_spreadsheet_status")
    installDate = JavascriptDateField(source="install_date")

    def convert_status_to_spreadsheet_status(self, link):
        if link.status != Link.LinkStatus.ACTIVE:
            return str(link.status).lower()

        if link.type == Link.LinkType.FIBER:
            return "fiber"
        elif link.type == Link.LinkType.VPN:
            return "vpn"
        elif link.type == Link.LinkType.MMWAVE:
            return "60GHz"

        return "active"

    def get_to_install_number(self, link):
        return get_install_number_from_node(link.to_device.node)

    def get_from_install_number(self, link):
        return get_install_number_from_node(link.from_device.node)

    def get_fields(self):
        result = super().get_fields()
        # Rename `from_` to `from`
        from_ = result.pop("from_")

        new_fields = OrderedDict({"from": from_})
        for key, value in result.items():
            new_fields[key] = value

        return new_fields

    def to_representation(self, link):
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
    device = serializers.CharField(source="model_name")
    installDate = JavascriptDateField(source="install_date")

    def get_node_id(self, sector):
        return get_install_number_from_node(sector.node)

    def convert_status_to_spreadsheet_status(self, sector):
        return str(sector.status).lower()

    def to_representation(self, sector):
        result = super().to_representation(sector)

        # Remove null fields when applicable to match the existing interface
        for key in ["installDate"]:
            if result[key] is None:
                del result[key]

        return result
