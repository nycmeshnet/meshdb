from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from meshapi.models import Building, Install, Member
from meshapi.permissions import IsReadOnly
from meshapi.serializers import BuildingSerializer, InstallSerializer, MemberSerializer, UserSerializer

# TODO: Do we need more routes for just getting a NN and stuff?


# Home view
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_root(request, format=None):
    return Response("We're meshin'.")


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class BuildingList(generics.ListCreateAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class BuildingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class MemberList(generics.ListCreateAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class InstallList(generics.ListCreateAPIView):
    permission_classes = [permissions.DjangoModelPermissions | IsReadOnly]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


class InstallDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.DjangoModelPermissions | IsReadOnly]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer
