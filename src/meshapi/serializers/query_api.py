from rest_framework import serializers

from meshapi.models import Install


class QueryFormSerializer(serializers.ModelSerializer):
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

    street_address = serializers.CharField(source="building.street_address")
    city = serializers.CharField(source="building.city")
    state = serializers.CharField(source="building.state")
    zip_code = serializers.CharField(source="building.zip_code")

    name = serializers.CharField(source="member.name")
    primary_email_address = serializers.CharField(source="member.primary_email_address")
    stripe_email_address = serializers.CharField(source="member.stripe_email_address")
    additional_email_addresses = serializers.ListField(
        source="member.additional_email_addresses", child=serializers.CharField()
    )

    notes = serializers.SerializerMethodField("concat_all_notes")

    def concat_all_notes(self, install):
        return "\n".join(
            [notes for notes in [install.notes, install.building.notes, install.member.contact_notes] if notes]
        )
