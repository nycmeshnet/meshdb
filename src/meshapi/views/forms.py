import json
import time
from dataclasses import dataclass
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from meshapi.exceptions import AddressAPIError, AddressError
from meshapi.models import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN, Building, Install, Member
from meshapi.permissions import HasNNAssignPermission, LegacyNNAssignmentPassword
from meshapi.util.django_pglocks import advisory_lock
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
@advisory_lock("join_form_lock")
def join_form(request):
    request_json = json.loads(request.body)
    try:
        r = JoinFormRequest(**request_json)
    except TypeError as e:
        return Response({"detail": "Got incomplete form request"}, status=status.HTTP_400_BAD_REQUEST)

    if not r.ncl:
        return Response(
            {"detail": "You must agree to the Network Commons License!"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not validate_email_address(r.email):
        return Response({"detail": f"{r.email} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    if not validate_phone_number(r.phone):
        return Response({"detail": f"{r.phone} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    # We only support the five boroughs of NYC at this time
    if not NYCZipCodes.match_zip(r.zip):
        return Response(
            {
                "detail": "Non-NYC registrations are not supported at this time. Check back later, or email support@nycmesh.net"
            },
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
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # If we get any other error, then there was probably an issue
        # using the API, and we should wait a bit and re-try
        except (AddressAPIError, Exception) as e:
            print(e)
            print("(NYC) Something went wrong validating the address. Re-trying...")
            time.sleep(3)
    # If we run out of tries, bail.
    if nyc_addr_info == None:
        return Response(
            {"detail": "Your address could not be validated."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Check if there's an existing member. Dedupe on email for now.
    # A member can have multiple install requests
    existing_members = Member.objects.filter(
        Q(primary_email_address=r.email)
        | Q(stripe_email_address=r.email)
        | Q(additional_email_addresses__contains=[r.email])
    )
    join_form_member = (
        existing_members[0]
        if len(existing_members) > 0
        else Member(
            name=r.first_name + " " + r.last_name,
            primary_email_address=r.email,
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
        return Response(
            {"detail": "There was a problem saving your Member information"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        join_form_building.save()
    except IntegrityError as e:
        print(e)
        # Delete the member and bail
        join_form_member.delete()
        return Response(
            {"detail": "There was a problem saving your Building information"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        join_form_install.save()
    except IntegrityError as e:
        print(e)
        # Delete the member, building (if we just created it), and bail
        join_form_member.delete()
        if len(existing_buildings) == 0:
            join_form_building.delete()
        return Response(
            {"detail": "There was a problem saving your Install information"}, status=status.HTTP_400_BAD_REQUEST
        )

    print(
        f"JoinForm submission success. building_id: {join_form_building.id}, member_id: {join_form_member.id}, install_number: {join_form_install.install_number}"
    )

    return Response(
        {
            "detail": "Thanks! A volunteer will email you shortly",
            "building_id": join_form_building.id,
            "member_id": join_form_member.id,
            "install_number": join_form_install.install_number,
            # If this is an existing member, then set a flag to let them know we have
            # their information in case they need to update anything.
            "member_exists": True if len(existing_members) > 0 else False,
        },
        status=status.HTTP_201_CREATED,
    )


def get_next_available_network_number() -> int:
    """
    This function finds, and marks as re-assigned, the next install whose number can be re-assigned
    for use as a network number. This is non-trivial becuause we need to exclude installs that
    have non "REQUEST RECIEVED" statuses, as well as the set of all NNs that have been assigned
    to any other installs for any reason
    :return: the integer for the next available network number
    """

    defined_nns = set(
        Install.objects.exclude(install_status=Install.InstallStatus.REQUEST_RECEIVED, network_number__isnull=True)
        .order_by("install_number")
        .values_list("install_number", flat=True)
    ).union(set(Install.objects.values_list("network_number", flat=True)))

    # Find the first valid NN that isn't in use
    free_nn = next(i for i in range(NETWORK_NUMBER_MIN, NETWORK_NUMBER_MAX + 1) if i not in defined_nns)

    # Sanity check to make sure we don't assign something crazy. This is done by the query above,
    # but we want to be super sure we don't violate these constraints so we check it here
    if free_nn < NETWORK_NUMBER_MIN or free_nn > NETWORK_NUMBER_MAX:
        raise ValueError(f"Invalid NN: {free_nn}")

    # The number we are about to assign should not be connected to any existing installs as
    # an NN. Again, the above logic should do this, but we REALLY care about this not happening
    already_in_use_nn_qs = Install.objects.filter(network_number=free_nn)
    if len(already_in_use_nn_qs):
        raise ValueError(
            f"Invalid NN: {free_nn} is already in use for "
            f"install number {already_in_use_nn_qs.first().install_number}"
        )

    # If we are re-assigning a number from another install, mark it with NN Assigned to indicate
    # that this has happened
    nn_donor_install: Optional[Install] = Install.objects.select_for_update().filter(install_number=free_nn).first()
    if nn_donor_install:
        # Double check that if we are re-assigning something that has been used before that it is
        # definitely unused. The logic above should do that, but this is so important that for
        # safety that we should double-check
        if (
            nn_donor_install.install_status != Install.InstallStatus.REQUEST_RECEIVED
            or nn_donor_install.network_number is not None
        ):
            raise ValueError(
                f"Invalid NN: {free_nn} has an install associated that "
                f"looks active (#{nn_donor_install.install_number})"
            )

        nn_donor_install.install_status = Install.InstallStatus.NN_REASSIGNED
        nn_donor_install.save()

    return free_nn


@dataclass
class NetworkNumberAssignmentRequest:
    install_number: int


@api_view(["POST"])
@permission_classes([HasNNAssignPermission | LegacyNNAssignmentPassword])
@transaction.atomic
@advisory_lock("nn_assignment_lock")
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
        return Response({"detail": "Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Here we use select_for_update() and select_related() to ensure we acquire a lock on all
        # rows related to the Install object at hand, so that for example, the attached building
        # isn't changed underneath us
        nn_install = Install.objects.select_for_update().select_related().get(install_number=r.install_number)
    except Exception as e:
        print(f'NN Request failed. Could not get Install w/ Install Number "{r.install_number}": {e}')
        return Response({"detail": "Install Number not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check if the install already has a network number
    if nn_install.network_number != None:
        message = f"This Install Number ({r.install_number}) already has a Network Number ({nn_install.network_number}) associated with it!"
        print(message)
        return Response(
            {
                "detail": message,
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
        try:
            free_nn = get_next_available_network_number()
        except ValueError as exception:
            return Response({"detail": f"NN Request failed. {exception}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Set the next free NN on both the install and the Building
        nn_install.network_number = free_nn
        nn_building.primary_nn = free_nn

    nn_install.install_status = Install.InstallStatus.ACTIVE

    try:
        nn_building.save()
        nn_install.save()
    except IntegrityError as e:
        print(e)
        return Response(
            {"detail": "NN Request failed. Could not save node number."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "detail": "Network Number has been assigned!",
            "building_id": nn_building.id,
            "install_number": nn_install.install_number,
            "network_number": nn_install.network_number,
            "created": True,
        },
        status=status.HTTP_201_CREATED,
    )
