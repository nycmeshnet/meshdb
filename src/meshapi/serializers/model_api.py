from rest_framework import serializers

from meshapi.models import Building, Install, Link, Member, Sector


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"

    installs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    links_from = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    links_to = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    sectors = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses = serializers.ReadOnlyField()
    installs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)


class InstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = "__all__"


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = "__all__"


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"
