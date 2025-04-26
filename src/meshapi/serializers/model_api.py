from datetime import timezone

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from meshapi.models import (
    LOS,
    AccessPoint,
    Building,
    Device,
    Install,
    InstallFeeBillingDatum,
    Link,
    Member,
    Node,
    Sector,
)
from meshapi.serializers.nested_key_object_related_field import NestedKeyObjectRelatedField, NestedKeyRelatedMixIn


class BuildingSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"
        extra_kwargs = {
            "primary_node": {"additional_keys": ("network_number",)},
            "nodes": {"additional_keys": ("network_number",), "required": False},
        }

    installs = NestedKeyObjectRelatedField(many=True, read_only=True, additional_keys=("install_number",))


class MemberSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses: serializers.ReadOnlyField = serializers.ReadOnlyField()
    all_phone_numbers: serializers.ReadOnlyField = serializers.ReadOnlyField()

    installs = NestedKeyObjectRelatedField(many=True, read_only=True, additional_keys=("install_number",))


class InstallSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    serializer_related_field = NestedKeyObjectRelatedField

    class Meta:
        model = Install
        fields = "__all__"
        extra_kwargs = {
            "node": {"additional_keys": ("network_number",)},
            "install_number": {"read_only": True},
        }

    request_date = serializers.DateTimeField(default_timezone=timezone.utc)
    install_fee_billing_datum = NestedKeyObjectRelatedField(
        allow_null=True,
        read_only=True,
        additional_keys_display_permission="meshapi.view_installfeebillingdatum",
        additional_keys=(
            "status",
            "billing_date",
            "invoice_number",
            "notes",
        ),
    )


class NodeSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = "__all__"
        extra_kwargs = {
            "network_number": {
                "validators": [
                    UniqueValidator(
                        queryset=Node.objects.all(),
                        message="node with this network number already exists.",
                    )
                ],
            }
        }

    buildings = NestedKeyObjectRelatedField(many=True, read_only=True)
    devices = NestedKeyObjectRelatedField(many=True, read_only=True)
    installs = NestedKeyObjectRelatedField(many=True, read_only=True, additional_keys=("install_number",))


class NodeEditSerializer(NodeSerializer):
    class Meta(NodeSerializer.Meta):
        read_only_fields = ("network_number",)


class LinkSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = "__all__"


class DeviceSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"
        extra_kwargs = {
            "node": {"additional_keys": ("network_number",)},
        }

    latitude = serializers.FloatField(
        read_only=True,
        help_text="Approximate Device latitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    longitude = serializers.FloatField(
        read_only=True,
        help_text="Approximate Device longitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    altitude = serializers.FloatField(
        read_only=True,
        help_text='Approximate Device altitude in "absolute" meters above mean sea level '
        "(this is read through from the attached Node object, not stored separately)",
    )

    links_from = NestedKeyObjectRelatedField(many=True, read_only=True)
    links_to = NestedKeyObjectRelatedField(many=True, read_only=True)


class SectorSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"
        extra_kwargs = {
            "node": {"additional_keys": ("network_number",)},
        }

    latitude = serializers.FloatField(
        read_only=True,
        help_text="Approximate Device latitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    longitude = serializers.FloatField(
        read_only=True,
        help_text="Approximate Device longitude in decimal degrees "
        "(this is read through from the attached Node object, not stored separately)",
    )
    altitude = serializers.FloatField(
        read_only=True,
        help_text='Approximate Device altitude in "absolute" meters above mean sea level '
        "(this is read through from the attached Node object, not stored separately)",
    )

    links_from = NestedKeyObjectRelatedField(many=True, read_only=True)
    links_to = NestedKeyObjectRelatedField(many=True, read_only=True)


class AccessPointSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = AccessPoint
        fields = "__all__"
        extra_kwargs = {
            "node": {"additional_keys": ("network_number",)},
        }

    links_from = NestedKeyObjectRelatedField(many=True, read_only=True)
    links_to = NestedKeyObjectRelatedField(many=True, read_only=True)


class LOSSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    class Meta:
        model = LOS
        fields = "__all__"


class InstallFeeBillingDatumSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    serializer_related_field = NestedKeyObjectRelatedField

    class Meta:
        model = InstallFeeBillingDatum
        fields = "__all__"
        extra_kwargs = {
            "install": {"additional_keys": ("install_number",)},
        }
