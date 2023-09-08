from django.contrib.auth.models import User
from rest_framework import generics, permissions
from meshapi.models import Building, Member, Install, Request
from meshapi.serializers import (
    UserSerializer,
    BuildingSerializer,
    MemberSerializer,
    InstallSerializer,
    RequestSerializer,
)
from meshapi.permissions import IsMeshInstaller, IsMeshMember
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


# Home view
@api_view(["GET"])
def api_root(request, format=None):
    return Response("We're meshin'.")
    # return Response({
    #     'installs': reverse('install-list', request=request, format=format),
    #     'requests': reverse('request-list', request=request, format=format)
    # })


class UserList(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer


# === BUILDINGS ===


class BuildingList(generics.ListCreateAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class BuildingDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


# === MEMBER ===


class MemberList(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


# === INSTALL ===


class InstallList(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser, IsMeshMember]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


class InstallDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser, IsMeshMember]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


# === REQUEST ===


class RequestList(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Request.objects.all()
    serializer_class = RequestSerializer


class RequestDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
