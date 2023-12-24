from dataclasses import dataclass
import json
from json.decoder import JSONDecodeError
import time
from django.utils import timezone
from geopy.exc import GeocoderUnavailable
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework import generics, permissions
from meshapi.models import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN, Building, Member, Install
from meshapi.serializers import (
    UserSerializer,
    BuildingSerializer,
    MemberSerializer,
    InstallSerializer,
)
from meshapi.permissions import (
    BuildingListCreatePermissions,
    BuildingRetrieveUpdateDestroyPermissions,
    MemberListCreatePermissions,
    MemberRetrieveUpdateDestroyPermissions,
    InstallListCreatePermissions,
    InstallRetrieveUpdateDestroyPermissions,
    NetworkNumberAssignmentPermissions,
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

    # Check if there's an existing member. Dedupe on email for now.
    # A member can have multiple install requests
    existing_members = Member.objects.filter(
        email_address=r.email,
    )
    join_form_member = (
        existing_members[0]
        if len(existing_members) > 0
        else Member(
            first_name=r.first_name,
            last_name=r.last_name,
            email_address=r.email,
            phone_number=r.phone,
            slack_handle=None,
        )
    )

    # If this is an existing member, update the name and phone with whatever
    # new info they gave us
    if len(existing_members) > 0:
        join_form_member.first_name = r.first_name
        join_form_member.last_name = r.last_name
        join_form_member.phone_number = r.phone

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
            primary_nn=None,
            install_date=None,
            abandon_date=None,
        )
    )

    join_form_install = Install(
        network_number=None,
        install_status=Install.InstallStatus.OPEN,
        ticket_id=None,
        request_date=timezone.now(),
        install_date=None,
        abandon_date=None,
        building_id=join_form_building,
        unit=r.apartment,
        roof_access=r.roof_access,
        member_id=join_form_member,
        notes=f"Referral: r.referral" if len(r.referral) > 0 else "",
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
        join_form_install.save()
    except IntegrityError as e:
        print(e)
        # Delete the member, building (if we just created it), and bail
        join_form_member.delete()
        if len(existing_buildings) == 0:
            join_form_building.delete()
        return Response("Could not save request", status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "building_id": join_form_building.id,
            "member_id": join_form_member.id,
            "install_number": join_form_install.install_number,
        },
        status=status.HTTP_201_CREATED,
    )


@dataclass
class NetworkNumberAssignmentRequest:
    install_number: int


@api_view(["POST"])
@permission_classes([NetworkNumberAssignmentPermissions])
def network_number_assignment(request):
    """
    Takes an install number, and assigns the install a network number,
    deduping using the other buildings in our database.
    """

    try:
        request_json = json.loads(request.body)
        r = NetworkNumberAssignmentRequest(**request_json)
    except (TypeError, JSONDecodeError) as e:
        print(f"NN Request failed. Could not decode request: {e}")
        return Response({"Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        nn_install = Install.objects.get(install_number=r.install_number)
    except Exception as e:
        print(f'NN Request failed. Could not get Install w/ Install Number "{r.install_number}": {e}')
        return Response({"Install Number not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check if the install already has a network number
    if nn_install.network_number != None:
        message = f"NN Request failed. This Install Number already has a Network Number associated with it! ({nn_install.network_number})"
        print(message)
        return Response(message, status=status.HTTP_409_CONFLICT)

    nn_building = nn_install.building_id

    # If the building already has a primary NN, then use that.
    if nn_building.primary_nn is not None:
        nn_install.network_number = nn_building.primary_nn
    else:
        free_nn = None

        defined_nns = set(Install.objects.values_list("network_number", flat=True))

        # Find the first valid NN that isn't in use
        free_nn = next(i for i in range(NETWORK_NUMBER_MIN, NETWORK_NUMBER_MAX + 1) if i not in defined_nns)

        # Set the NN on both the install and the Building
        nn_install.network_number = free_nn
        nn_building.primary_nn = free_nn

    nn_install.install_status = Install.InstallStatus.ACTIVE
    nn_install.install_date = timezone.now()
    nn_building.install_date = nn_install.install_date

    try:
        nn_building.save()
        nn_install.save()
    except IntegrityError as e:
        print(e)
        return Response("NN Request failed. Could not save node number.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {
            "building_id": nn_building.id,
            "install_number": nn_install.install_number,
            "network_number": nn_install.network_number,
        },
        status=status.HTTP_200_OK,
    )
