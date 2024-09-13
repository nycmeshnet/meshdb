from typing import List, Optional, TypedDict
from uuid import UUID

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector

InstallRef = TypedDict("InstallRef", {"id": UUID, "install_number": int})
NodeRef = TypedDict("NodeRef", {"id": UUID, "network_number": Optional[int]})


class InstallsForeignKeyMixin:
    def get_installs(self, obj: Building | Node | Member) -> List[InstallRef]:
        return list(obj.installs.order_by("install_number").values("id", "install_number"))


class NodesForeignKeyMixin:
    def get_nodes(self, obj: Building) -> List[NodeRef]:
        return list(obj.nodes.order_by("network_number").values("id", "network_number"))


class BuildingSerializer(serializers.ModelSerializer, InstallsForeignKeyMixin, NodesForeignKeyMixin):
    class Meta:
        model = Building
        fields = "__all__"

    installs = serializers.SerializerMethodField()
    nodes = serializers.SerializerMethodField()

    primary_network_number: serializers.IntegerField = serializers.IntegerField(
        source="primary_node.network_number",
        read_only=True,
    )


class MemberSerializer(serializers.ModelSerializer, InstallsForeignKeyMixin):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses: serializers.ReadOnlyField = serializers.ReadOnlyField()
    all_phone_numbers: serializers.ReadOnlyField = serializers.ReadOnlyField()
    installs = serializers.SerializerMethodField()


class InstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = "__all__"

    network_number = serializers.IntegerField(read_only=True)
    install_number = serializers.IntegerField(read_only=True)


class NodeSerializer(serializers.ModelSerializer, InstallsForeignKeyMixin):
    class Meta:
        model = Node
        fields = "__all__"

    network_number = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[
            UniqueValidator(
                queryset=Node.objects.all(),
                message="node with this network number already exists.",
            )
        ],
    )

    buildings: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    devices: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    installs = serializers.SerializerMethodField()


class NodeEditSerializer(NodeSerializer):
    network_number = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[
            UniqueValidator(
                queryset=Node.objects.all(),
                message="node with this network number already exists.",
            )
        ],
        read_only=True,
    )


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = "__all__"


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"

    network_number = serializers.IntegerField(read_only=True)

    latitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text="Approximate Device latitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    longitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text="Approximate Device longitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    altitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text='Approximate Device altitude in "absolute" meters above mean sea level '
        "(this is read through from the attached Node object, not stored separately)",
    )

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"

    network_number = serializers.IntegerField(read_only=True)

    latitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text="Approximate Device latitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    longitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text="Approximate Device longitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    altitude: serializers.ReadOnlyField = serializers.ReadOnlyField(
        help_text='Approximate Device altitude in "absolute" meters above mean sea level '
        "(this is read through from the attached Node object, not stored separately)",
    )

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class AccessPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPoint
        fields = "__all__"

    network_number = serializers.IntegerField(read_only=True)

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class LOSSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOS
        fields = "__all__"
