import datetime
from collections import OrderedDict

from rest_framework import serializers

from meshapi.models import Install, Link, Sector


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


def get_install_number_from_building(building):
    installs = building.install_set.all()
    if len(installs) == 0:
        if building.primary_nn:
            return building.primary_nn
        else:
            raise ValueError(
                f"Building with ID {building} is invalid for install "
                f"number conversion, no attached installs or NN assigned"
            )
    else:
        return min(install.install_number for install in installs)


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
    name = serializers.CharField(source="building.node_name")
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

    def get_start_of_notes(self, install):
        if install.notes:
            note_parts = install.notes.split("\n")
            return note_parts[1] if len(note_parts) > 1 and note_parts[1] != "None" else None
        return None

    def convert_status_to_spreadsheet_status(self, install):
        if install.install_status == Install.InstallStatus.REQUEST_RECEIVED:
            return None
        elif install.install_status == Install.InstallStatus.PENDING:
            return "Interested"
        elif install.install_status == Install.InstallStatus.BLOCKED:
            return "No Los"
        elif install.install_status == Install.InstallStatus.ACTIVE:
            return "Installed"
        elif install.install_status == Install.InstallStatus.INACTIVE:
            return "Powered Off"
        elif install.install_status == Install.InstallStatus.CLOSED:
            return "Abandoned"

        return install.install_status

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
        return get_install_number_from_building(link.to_building)

    def get_from_install_number(self, link):
        return get_install_number_from_building(link.from_building)

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
    device = serializers.CharField(source="device_name")
    installDate = JavascriptDateField(source="install_date")

    def get_node_id(self, sector):
        return get_install_number_from_building(sector.building)

    def convert_status_to_spreadsheet_status(self, sector):
        return str(sector.status).lower()

    def to_representation(self, sector):
        result = super().to_representation(sector)

        # Remove null fields when applicable to match the existing interface
        for key in ["installDate"]:
            if result[key] is None:
                del result[key]

        return result
