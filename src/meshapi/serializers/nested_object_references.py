from rest_framework import serializers

from meshapi.models import Install
from meshapi.serializers import NestedKeyObjectRelatedField, NestedKeyRelatedMixIn


class InstallNestedRefSerializer(NestedKeyRelatedMixIn, serializers.ModelSerializer):
    serializer_related_field = NestedKeyObjectRelatedField

    class Meta:
        model = Install
        fields = ["install_number", "id", "node"]
        extra_kwargs = {
            "node": {"additional_keys": ("network_number",)},
            "install_number": {"read_only": True},
        }
