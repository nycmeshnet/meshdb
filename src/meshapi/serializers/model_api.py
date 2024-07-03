from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        exclude = ("primary_node", "nodes")

    installs: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    network_numbers: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="nodes", many=True, read_only=True
    )
    primary_network_number: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="primary_node", queryset=Node.objects.all(), required=False, allow_null=True
    )


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses: serializers.ReadOnlyField = serializers.ReadOnlyField()
    installs: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class InstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        exclude = ("node",)

    network_number = serializers.PrimaryKeyRelatedField(
        source="node", queryset=Node.objects.all(), required=False, allow_null=True
    )


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = "__all__"

    network_number = serializers.IntegerField(
        required=False,
        allow_null=False,
        validators=[UniqueValidator(queryset=Node.objects.all())],
        read_only=True,
    )
    buildings: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    devices: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = "__all__"


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        exclude = ("node",)

    network_number = serializers.PrimaryKeyRelatedField(
        source="node", queryset=Node.objects.all(), required=True, allow_null=False
    )

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        exclude = ("node",)

    network_number: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="node", queryset=Node.objects.all(), required=True, allow_null=False
    )

    links_from: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
