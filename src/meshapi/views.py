from dataclasses import dataclass
import json
import time
from geopy.exc import GeocoderUnavailable
import requests
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
from meshapi.validation import (
    OSMAddressInfo,
    validate_phone_number,
    validate_email_address,
    NYCAddressInfo,
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
@dataclass
class JoinFormRequest:
    first_name: str
    last_name: str
    email: str
    phone: str
    street_address: str
    city: str
    state: str
    zip: int
    apartment: str
    roof_access: bool
    referral: str


@api_view(["POST"])
def join_form(request):
    request_json = json.loads(request.body)
    try:
        r = JoinFormRequest(**request_json)
    except TypeError as e:
        return Response({"Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    print("Validating Email...")
    if not validate_email_address(r.email):
        return Response({f"{r.email} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    print("Validating Phone...")
    if not validate_phone_number(r.phone):
        return Response({f"{r.phone} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    print("Validating Address...")
    try:
        osm_addr_info = OSMAddressInfo(r.street_address, r.city, r.state, r.zip)
        if not osm_addr_info.nyc:
            print("(OSM) Address is not NYC")
    except ValueError as e:
        print(e)
        return Response(f"(OSM) Address not found", status=status.HTTP_404_NOT_FOUND)
    except AttributeError as e:
        print(e)
        return Response(f"(OSM) Error validating address: {str(e)}", status=status.HTTP_400_BAD_REQUEST)
    except GeocoderUnavailable as e:
        print(e)
        return Response(f"(OSM) Error validating address: {str(e)}", status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Only bother with the NYC APIs if we know the address is in NYC
    print(osm_addr_info)
    nyc_addr_info = None
    if osm_addr_info.nyc:
        for attempts in range(0, 2):
            try:
                nyc_addr_info = NYCAddressInfo(r.street_address, r.city, r.state, r.zip)
            except requests.exceptions.HTTPError as e:
                print(e)
                return Response(str(e), status=status.HTTP_404_NOT_FOUND)
            except ValueError as e:
                print(e)
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                if attempts == 1:
                    return Response(f"(NYC) Error validating address", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    print("(NYC) Something went wrong validating the address. Re-trying...")
                    time.sleep(3)

    existing_members = Member.objects.filter(
        first_name=r.first_name,
        last_name=r.last_name,
        email_address=r.email,
        phone_number=r.phone,
    )

    if len(existing_members) > 0:
        return Response({"Member already exists"}, status=status.HTTP_400_BAD_REQUEST)

    join_form_member = Member(
        first_name=r.first_name,
        last_name=r.last_name,
        email_address=r.email,
        phone_number=r.phone,
        slack_handle="",
    )

    try:
        join_form_member.save()
    except IntegrityError as e:
        print(e)
        return Response({"Could not save member."}, status=status.HTTP_400_BAD_REQUEST)

    existing_buildings = Building.objects.filter(
        street_address=r.street_address,
        city=r.city,
        state=r.state,
        zip_code=r.zip,
    )

    join_form_building = (
        existing_buildings[0]
        if len(existing_buildings) > 0
        else Building(
            bin=nyc_addr_info.bin if nyc_addr_info is not None else -1,
            building_status=Building.BuildingStatus.INACTIVE,
            street_address=r.street_address,
            city=r.city,
            state=r.state,
            zip_code=r.zip,
            latitude=nyc_addr_info.latitude if nyc_addr_info is not None else osm_addr_info.latitude,
            longitude=nyc_addr_info.longitude if nyc_addr_info is not None else osm_addr_info.longitude,
            altitude=nyc_addr_info.altitude if nyc_addr_info is not None else osm_addr_info.altitude,
            network_number=None,
            install_date=None,
            abandon_date=None,
        )
    )
    try:
        join_form_building.save()
    except IntegrityError as e:
        print(e)
        return Response({"Could not save building"}, status=status.HTTP_400_BAD_REQUEST)

    join_form_request = Request(
        request_status=Request.RequestStatus.OPEN,
        roof_access=r.roof_access,
        referral=r.referral,
        ticket_id=None,
        member_id=join_form_member,
        building_id=join_form_building,
        unit=r.apartment,
        install_id=None,
    )

    try:
        join_form_request.save()
    except IntegrityError as e:
        print(e)
        return Response({"Could not save request"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "building_id": join_form_building.id,
        "member_id": join_form_member.id,
        "request_id": join_form_request.id
    }, status=status.HTTP_201_CREATED)
