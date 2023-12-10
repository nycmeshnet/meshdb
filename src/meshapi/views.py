from dataclasses import dataclass
import json
import time
from geopy.exc import GeocoderUnavailable
import requests
from django.contrib.auth.models import User, models
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
    NewNodePermissions,
    RequestListCreatePermissions,
    RequestRetrieveUpdateDestroyPermissions,
)
from meshapi.validation import (
    OSMAddressInfo,
    validate_phone_number,
    validate_email_address,
    NYCAddressInfo,
)
from meshapi.exceptions import AddressError, AddressAPIError
from rest_framework.decorators import api_view, permission_classes
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

    if not validate_email_address(r.email):
        return Response(f"{r.email} is not a valid email", status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    if not validate_phone_number(r.phone):
        return Response(f"{r.phone} is not a valid phone number", status=status.HTTP_400_BAD_REQUEST)

    # Query the Open Street Map to validate and "standardize" the member's
    # inputs. We're going to use this as the canonical address, and then
    # supplement with NYC API information
    osm_addr_info = None
    attempts_remaining = 2
    while attempts_remaining > 0:
        attempts_remaining -= 1
        try:
            osm_addr_info = OSMAddressInfo(r.street_address, r.city, r.state, r.zip)
            if not osm_addr_info.nyc:
                print(
                    f"(OSM) Address '{osm_addr_info.street_address}, {osm_addr_info.city}, {osm_addr_info.state} {osm_addr_info.zip}' is not in NYC"
                )
            break
        # If the user has given us an invalid address, tell them to buzz off.
        except AddressError as e:
            print(e)
            return Response(
                f"(OSM) Address '{r.street_address}, {r.city}, {r.state} {r.zip}' not found",
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssertionError as e:
            print(e)
            return Response("Unexpected internal state", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # If the API gives us an error, then try again
        except (GeocoderUnavailable, Exception) as e:
            print(e)
            print("(OSM) Something went wrong validating the address. Re-trying...")
            time.sleep(3)
    # If we try multiple times without success, bail.
    if osm_addr_info == None:
        return Response("(OSM) Error validating address", status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Only bother with the NYC APIs if we know the address is in NYC
    nyc_addr_info = None
    if osm_addr_info.nyc:
        attempts_remaining = 2
        while attempts_remaining > 0:
            attempts_remaining -= 1
            try:
                nyc_addr_info = NYCAddressInfo(
                    osm_addr_info.street_address, osm_addr_info.city, osm_addr_info.state, osm_addr_info.zip
                )
                break
            # If the user has given us an invalid address. Tell them to buzz
            # off.
            except AddressError as e:
                print(e)
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            # If we get any other error, then there was probably an issue
            # using the API, and we should wait a bit and re-try
            except (AddressAPIError, Exception) as e:
                print(e)
                print("(NYC) Something went wrong validating the address. Re-trying...")
                time.sleep(3)
        # If we run out of tries, bail.
        if nyc_addr_info == None:
            return Response("(NYC) Error validating address", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Check if there's an existing member, and bail if there is
    existing_members = Member.objects.filter(
        first_name=r.first_name,
        last_name=r.last_name,
        email_address=r.email,
        phone_number=r.phone,
    )
    if len(existing_members) > 0:
        return Response("Member already exists", status=status.HTTP_400_BAD_REQUEST)

    join_form_member = Member(
        first_name=r.first_name,
        last_name=r.last_name,
        email_address=r.email,
        phone_number=r.phone,
        slack_handle="",
    )

    # If the address is in NYC, then try to look up by BIN, otherwise fallback
    # to address
    existing_buildings = None
    if nyc_addr_info is not None:
        existing_buildings = Building.objects.filter(bin=nyc_addr_info.bin)
    else:
        existing_buildings = Building.objects.filter(
            street_address=osm_addr_info.street_address,
            city=osm_addr_info.city,
            state=osm_addr_info.state,
            zip_code=osm_addr_info.zip,
        )

    join_form_building = (
        existing_buildings[0]
        if len(existing_buildings) > 0
        else Building(
            bin=nyc_addr_info.bin if nyc_addr_info is not None else -1,
            building_status=Building.BuildingStatus.INACTIVE,
            street_address=osm_addr_info.street_address,
            city=osm_addr_info.city,
            state=osm_addr_info.state,
            zip_code=int(osm_addr_info.zip),
            latitude=nyc_addr_info.latitude if nyc_addr_info is not None else osm_addr_info.latitude,
            longitude=nyc_addr_info.longitude if nyc_addr_info is not None else osm_addr_info.longitude,
            altitude=nyc_addr_info.altitude if nyc_addr_info is not None else osm_addr_info.altitude,
            network_number=None,
            install_date=None,
            abandon_date=None,
        )
    )

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
        join_form_member.save()
    except IntegrityError as e:
        print(e)
        return Response("Could not save member.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        join_form_building.save()
    except IntegrityError as e:
        print(e)
        # Delete the member and bail
        join_form_member.delete()
        return Response("Could not save building", status=status.HTTP_400_BAD_REQUEST)

    try:
        join_form_request.save()
    except IntegrityError as e:
        print(e)
        # Delete the member, building (if we just created it), and bail
        join_form_member.delete()
        if len(existing_buildings) == 0:
            join_form_building.delete()
        return Response("Could not save request", status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {"building_id": join_form_building.id, "member_id": join_form_member.id, "request_id": join_form_request.id},
        status=status.HTTP_201_CREATED,
    )


@dataclass
class NewNodeRequest:
    meshapi_building_id: int


@api_view(["POST"])
@permission_classes([NewNodePermissions])
def new_node(request):
    """
    Takes in an existing building ID (not an NYC BIN, one of ours), and assigns
    it a network number, deduping using the other buildings in our database.
    First 100 NNs are reserved.
    """

    request_json = json.loads(request.body)
    try:
        r = NewNodeRequest(**request_json)
    except TypeError as e:
        print(e)
        return Response({"Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    new_node_building = Building.objects.get(id=r.meshapi_building_id)

    free_nn = 0

    # Get the highest in-use NN
    max_nn = Building.objects.aggregate(models.Max("network_number"))["network_number__max"]

    defined_nns = set(Building.objects.values_list("network_number", flat=True))

    # Find the first valid NN that isn't in use
    free_nn = next(i for i in range(101, max_nn + 1) if i not in defined_nns)

    # Set the NN
    new_node_building.network_number = free_nn
    new_node_building.save()

    return Response(
        {"building_id": new_node_building.id, "node_number": new_node_building.network_number},
        status=status.HTTP_200_OK,
    )
