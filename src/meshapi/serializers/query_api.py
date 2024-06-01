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
            "phone_number",
            "additional_phone_numbers",
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
    phone_number = serializers.CharField(source="member.phone_number")
    additional_phone_numbers = serializers.ListField(
        source="member.additional_phone_numbers", child=serializers.CharField()
    )

    network_number = serializers.IntegerField(source="node.network_number", allow_null=True)

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
