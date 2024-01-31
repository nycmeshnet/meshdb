import json
import time
from dataclasses import dataclass
from datetime import datetime
from json.decoder import JSONDecodeError

from django.conf import os
from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from meshapi.exceptions import AddressAPIError, AddressError
from meshapi.models import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN, Building, Install, Member
from meshapi.permissions import HasNNAssignPermission, LegacyNNAssignmentPassword
from meshapi.validation import NYCAddressInfo, validate_email_address, validate_phone_number
from meshapi.zips import NYCZipCodes
from meshdb.utils.spreadsheet_import.building.constants import AddressTruthSource


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
    ncl: bool


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def join_form(request):
    request_json = json.loads(request.body)
    try:
        r = JoinFormRequest(**request_json)
    except TypeError as e:
        return Response({"Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    if not r.ncl:
        return Response("You must agree to the Network Commons License!", status=status.HTTP_400_BAD_REQUEST)

    if not validate_email_address(r.email):
        return Response(f"{r.email} is not a valid email", status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    if not validate_phone_number(r.phone):
        return Response(f"{r.phone} is not a valid phone number", status=status.HTTP_400_BAD_REQUEST)

    # We only support the five boroughs of NYC at this time
    if not NYCZipCodes.match_zip(r.zip):
        return Response(
            "Sorry, we don’t support non NYC registrations at this time, check back later or email support@nycmesh.net",
            status=status.HTTP_400_BAD_REQUEST,
        )

    nyc_addr_info = None
    attempts_remaining = 2
    while attempts_remaining > 0:
        attempts_remaining -= 1
        try:
            nyc_addr_info = NYCAddressInfo(r.street_address, r.city, r.state, r.zip)
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
            name=r.first_name + " " + r.last_name,
            email_address=r.email,
            phone_number=r.phone,
            slack_handle=None,
        )
    )

    # If the address is in NYC, then try to look up by BIN, otherwise fallback
    # to address
    existing_buildings = Building.objects.filter(bin=nyc_addr_info.bin)

    join_form_building = (
        existing_buildings[0]
        if len(existing_buildings) > 0
        else Building(
            bin=nyc_addr_info.bin if nyc_addr_info is not None else -1,
            building_status=Building.BuildingStatus.INACTIVE,
            street_address=nyc_addr_info.street_address,
            city=nyc_addr_info.city,
            state=nyc_addr_info.state,
            zip_code=int(nyc_addr_info.zip),
            latitude=nyc_addr_info.latitude,
            longitude=nyc_addr_info.longitude,
            altitude=nyc_addr_info.altitude,
            address_truth_sources=[AddressTruthSource.NYCPlanningLabs],
            primary_nn=None,
        )
    )

    join_form_install = Install(
        network_number=None,
        install_status=Install.InstallStatus.REQUEST_RECEIVED,
        ticket_id=None,
        request_date=datetime.today(),
        install_date=None,
        abandon_date=None,
        building=join_form_building,
        unit=r.apartment,
        roof_access=r.roof_access,
        member=join_form_member,
        referral=r.referral,
        notes=None,
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

    print(
        f"JoinForm submission success. building_id: {join_form_building.id}, member_id: {join_form_member.id}, install_number: {join_form_install.install_number}"
    )

    return Response(
        {
            "building_id": join_form_building.id,
            "member_id": join_form_member.id,
            "install_number": join_form_install.install_number,
            # If this is an existing member, then set a flag to let them know we have
            # their information in case they need to update anything.
            "member_exists": True if len(existing_members) > 0 else False,
        },
        status=status.HTTP_201_CREATED,
    )


@dataclass
class NetworkNumberAssignmentRequest:
    install_number: int


@api_view(["POST"])
@permission_classes([HasNNAssignPermission | LegacyNNAssignmentPassword])
def network_number_assignment(request):
    """
    Takes an install number, and assigns the install a network number,
    deduping using the other buildings in our database.
    """

    try:
        request_json = json.loads(request.body)
        if "password" in request_json:
            del request_json["password"]

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
        message = f"This Install Number ({r.install_number}) already has a Network Number ({nn_install.network_number}) associated with it!"
        print(message)
        return Response(
            {
                "building_id": nn_install.building.id,
                "install_number": nn_install.install_number,
                "network_number": nn_install.network_number,
                "created": False,
            },
            status=status.HTTP_200_OK,
        )

    nn_building = nn_install.building

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
            "created": True,
        },
        status=status.HTTP_201_CREATED,
    )
