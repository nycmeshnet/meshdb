from django.contrib.auth.models import User
from rest_framework import serializers
from meshapi.models import Building, Member, Install, Request


class UserSerializer(serializers.ModelSerializer):
    buildings = serializers.PrimaryKeyRelatedField(many=True, queryset=Building.objects.all())
    members = serializers.PrimaryKeyRelatedField(many=True, queryset=Member.objects.all())
    installs = serializers.PrimaryKeyRelatedField(many=True, queryset=Install.objects.all())
    requests = serializers.PrimaryKeyRelatedField(many=True, queryset=Request.objects.all())

    class Meta:
        model = User
        fields = ["id", "username", "buildings", "installs", "requests"]


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"


class InstallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = "__all__"


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Install
        fields = "__all__"
