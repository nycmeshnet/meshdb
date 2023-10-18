import json
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework import generics, permissions
from meshapi.models import Building, Member, Install, Request
from meshapi.serializers import (
    UserSerializer,
    BuildingSerializer,
    MemberSerializer,
    InstallSerializer,
    RequestSerializer,
)
from meshapi.permissions import (
    BuildingListCreatePermissions,
    BuildingRetrieveUpdateDestroyPermissions,
    MemberListCreatePermissions,
    MemberRetrieveUpdateDestroyPermissions,
    InstallListCreatePermissions,
    InstallRetrieveUpdateDestroyPermissions,
    RequestListCreatePermissions,
    RequestRetrieveUpdateDestroyPermissions,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser


# Home view
@api_view(["GET"])
def api_root(request, format=None):
    return Response("We're meshin'.")


# === USERS ===


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
    permission_classes = [BuildingListCreatePermissions]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class BuildingDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [BuildingRetrieveUpdateDestroyPermissions]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


# TODO: Do we need more routes for just getting a NN and stuff?


# === MEMBER ===


class MemberList(generics.ListCreateAPIView):
    permission_classes = [MemberListCreatePermissions]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [MemberRetrieveUpdateDestroyPermissions]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


# === INSTALL ===


class InstallList(generics.ListCreateAPIView):
    permission_classes = [InstallListCreatePermissions]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


class InstallDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [InstallRetrieveUpdateDestroyPermissions]
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


# === REQUEST ===


# class RequestList(mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView):
#    queryset = Request.objects.all()
#    serializer_class = RequestSerializer
#
#    def get(self, request, *args, **kwargs):
#        return self.list(request, *args, **kwargs)
#
#    def post(self, request, *args, **kwargs):
#        if not request.user.is_superuser:
#            raise PermissionDenied("You do not have permission to delete this resource")
#        return self.create(request, *args, **kwargs)


class RequestList(generics.ListCreateAPIView):
    permission_classes = [RequestListCreatePermissions]
    queryset = Request.objects.all()
    serializer_class = RequestSerializer


class RequestDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [RequestRetrieveUpdateDestroyPermissions]
    queryset = Request.objects.all()
    serializer_class = RequestSerializer


# Join Form
@api_view(["POST"])
def join_form(request):
    request_json = json.loads(request.body)

    existing_members = Member.objects.filter(
        first_name=request_json.get("first_name"),
        last_name=request_json.get("last_name"),
        email_address=request_json.get("email"),
        phone_numer=request_json.get("phone"),
    )

    join_form_member = existing_members[0] if len(existing_members) > 0 else Member(
        first_name=request_json.get("first_name"),
        last_name=request_json.get("last_name"),
        email_address=request_json.get("email"),
        phone_numer=request_json.get("phone"),
        slack_handle="",
    )
    try:
        join_form_member.save()
    except IntegrityError as e:
        print(e)
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    existing_buildings = Building.objects.filter(
        street_address=request_json.get("street_address"),
        city=request_json.get("city"),
        state=request_json.get("state"),
        zip_code=request_json.get("zip"),
    )

    # TODO: Implement BIN lookup, lat/long, and altitude
    join_form_building = existing_buildings[0] if len(existing_buildings) > 0 else Building(
        bin=69,
        building_status=Building.BuildingStatus.INACTIVE,
        street_address=request_json.get("street_address"),
        city=request_json.get("city"),
        state=request_json.get("state"),
        zip_code=request_json.get("zip"),
        latitude=69,
        longitude=69,
        altitude=69,
        network_number=None,
        install_date=None,
        abandon_date=None,
    )

    try:
        join_form_building.save()
    except IntegrityError as e:
        print(e)
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    join_form_request = Request(
        request_status=Request.RequestStatus.OPEN,
        ticket_id=None,
        member_id=join_form_member,
        building_id=join_form_building,
        unit=request_json.get("unit"),
        install_id=None,
    )

    try:
        join_form_request.save()
    except IntegrityError as e:
        print(e)
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({}, status=status.HTTP_201_CREATED)
