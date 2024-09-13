from typing import List, Optional, TypedDict
from uuid import UUID

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector


class InstallReferenceSerializer(serializers.ModelSerializer):
    """Serialize an Install object with just the bare minimum fields to reference it from another serializer"""

    class Meta:
        model = Install
        fields = ("id", "install_number")


class NodeReferenceSerializer(serializers.ModelSerializer):
    """Serialize a Node object with just the bare minimum fields to reference it from another serializer"""

    class Meta:
        model = Node
        fields = ("id", "network_number")


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"

    installs = InstallReferenceSerializer(many=True)
    nodes = NodeReferenceSerializer(many=True)

    primary_node = NodeReferenceSerializer()


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses: serializers.ReadOnlyField = serializers.ReadOnlyField()
    all_phone_numbers: serializers.ReadOnlyField = serializers.ReadOnlyField()

    installs = InstallReferenceSerializer(many=True)


class InstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = "__all__"

    node = NodeReferenceSerializer()
    install_number = serializers.IntegerField(read_only=True)


class NodeSerializer(serializers.ModelSerializer):
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
    installs = InstallReferenceSerializer(many=True)


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

    node = NodeReferenceSerializer()

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

    node = NodeReferenceSerializer()

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

    node = NodeReferenceSerializer()

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class LOSSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOS
        fields = "__all__"
