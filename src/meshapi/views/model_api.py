from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from meshapi.models import Building, Install, Member
from meshapi.permissions import (
    BuildingListCreatePermissions,
    BuildingRetrieveUpdateDestroyPermissions,
    InstallListCreatePermissions,
    InstallRetrieveUpdateDestroyPermissions,
    MemberListCreatePermissions,
    MemberRetrieveUpdateDestroyPermissions,
)
from meshapi.serializers import BuildingSerializer, InstallSerializer, MemberSerializer, UserSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

# TODO: Do we need more routes for just getting a NN and stuff?

# Home view
@api_view(["GET"])
def api_root(request, format=None):
    return Response("We're meshin'.")


class UserList(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class BuildingList(generics.ListCreateAPIView):
    permission_classes = [BuildingListCreatePermissions]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class BuildingDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [BuildingRetrieveUpdateDestroyPermissions]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class MemberList(generics.ListCreateAPIView):
    permission_classes = [MemberListCreatePermissions]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [MemberRetrieveUpdateDestroyPermissions]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class InstallList(generics.ListCreateAPIView):
    permission_classes = [InstallListCreatePermissions]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


class InstallDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [InstallRetrieveUpdateDestroyPermissions]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer

