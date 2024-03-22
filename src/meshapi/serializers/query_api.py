from meshapi.models.building import Building
from meshapi.models.member import Member
from meshapi.models.node import Node
from rest_framework import serializers

from meshapi.models import Install


class QueryFormSerializer(serializers.ModelSerializer):
    """
    Objects which approximate the CSV output from the legacy docs query form. These approximately
    correspond to the spreadsheet row format, by flattening attributes across many models into a
    single JSON object
    """

    class Meta:
        model = Install
        fields = (
            "install_number",
            "street_address",
            "unit",
            "city",
            "state",
            "zip_code",
            "name",
            "primary_email_address",
            "stripe_email_address",
            "additional_email_addresses",
            "notes",
            "network_number",
            "status",
        )

    street_address = serializers.SerializerMethodField("find_street_address")
    city = serializers.SerializerMethodField("find_city")
    state = serializers.SerializerMethodField("find_state")
    zip_code = serializers.SerializerMethodField("find_zip_code")
    
    def find_street_address(self, obj):
        b = self.find_building(obj)
        if b:
            return b.street_address
        return None

    def find_city(self, obj):
        b = self.find_building(obj)
        if b:
            return b.city
        return None

    def find_state(self, obj):
        b = self.find_building(obj)
        if b:
            return b.state
        return None

    def find_zip_code(self, obj):
        b = self.find_building(obj)
        if b:
            return b.zip_code
        return None

    def find_building(self, obj):
        if type(obj) is Building:
            return obj
        elif type(obj) is Install:
            return obj.building
        elif type(obj) is Member:
            return obj.install.building
        elif type(obj) is Node:
            return obj.buildings[0]
        return None

    name = serializers.CharField(source="member.name")

    network_number = serializers.IntegerField(source="node.network_number")

    primary_email_address = serializers.CharField(source="member.primary_email_address")
    stripe_email_address = serializers.CharField(source="member.stripe_email_address")
    additional_email_addresses = serializers.ListField(
        source="member.additional_email_addresses", child=serializers.CharField()
    )

    notes = serializers.SerializerMethodField("concat_all_notes")

    def concat_all_notes(self, install: Install) -> str:
        note_sources = [notes for notes in [install.notes, install.building.notes, install.member.notes] if notes]
        if install.node and install.node.notes:
            note_sources.append(install.node.notes)

        return "\n".join(note_sources)
