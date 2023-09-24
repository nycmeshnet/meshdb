from django.contrib.auth.models import User
from rest_framework import serializers
from meshapi.models import Building, Member, Install, Request


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


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
        model = Request
        fields = "__all__"
