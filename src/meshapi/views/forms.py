import json
import logging
import operator
from dataclasses import dataclass
from datetime import date
from functools import reduce
from json.decoder import JSONDecodeError
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_dataclasses.serializers import DataclassSerializer

from meshapi.exceptions import AddressError
from meshapi.models import Building, Install, Member, Node
from meshapi.permissions import HasNNAssignPermission, LegacyNNAssignmentPassword
from meshapi.serializers import MemberSerializer
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.django_pglocks import advisory_lock
from meshapi.util.network_number import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN, get_next_available_network_number
from meshapi.validation import (
    NYCAddressInfo,
    geocode_nyc_address,
    normalize_phone_number,
    validate_email_address,
    validate_phone_number,
)
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


class JoinFormRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = JoinFormRequest


form_err_response_schema = inline_serializer("ErrorResponse", fields={"detail": serializers.CharField()})


@extend_schema_view(
    post=extend_schema(
        tags=["User Forms"],
        auth=[],
        summary="Register a new request for a potential mesh Install. "
        "Used by the join form posted on the nycmesh.net website",
        request=JoinFormRequestSerializer,
        responses={
            "201": OpenApiResponse(
                inline_serializer(
                    "JoinFormSuccessResponse",
                    fields={
                        "detail": serializers.CharField(),
                        "building_id": serializers.UUIDField(),
                        "member_id": serializers.UUIDField(),
                        "install_id": serializers.UUIDField(),
                        "install_number": serializers.IntegerField(),
                        "member_exists": serializers.BooleanField(),
                        "info_changed": serializers.CharField(),
                        "changed_info": JoinFormRequestSerializer(),
                    },
                ),
                description="Request received, an install has been created (along with member and "
                "building objects if necessary).",
            ),
            "400": OpenApiResponse(
                form_err_response_schema, description="Invalid request body JSON or missing required fields"
            ),
            "500": OpenApiResponse(form_err_response_schema, description="Unexpected internal error"),
        },
    ),
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@advisory_lock("join_form_lock")
def join_form(request: Request) -> Response:
    request_json = json.loads(request.body)
    try:
        r = JoinFormRequest(**request_json)
    except TypeError:
        logging.exception("TypeError while processing JoinForm")
        return Response({"detail": "Got incomplete form request"}, status=status.HTTP_400_BAD_REQUEST)

    if not r.ncl:
        return Response(
            {"detail": "You must agree to the Network Commons License!"}, status=status.HTTP_400_BAD_REQUEST
        )

    join_form_full_name = f"{r.first_name} {r.last_name}"

    if not r.email and not r.phone:
        return Response({"detail": "Must provide an email or phone number"}, status=status.HTTP_400_BAD_REQUEST)

    if r.email and not validate_email_address(r.email):
        return Response({"detail": f"{r.email} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    if r.phone and not validate_phone_number(r.phone):
        return Response({"detail": f"{r.phone} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    formatted_phone_number = normalize_phone_number(r.phone) if r.phone else None

    try:
        nyc_addr_info: Optional[NYCAddressInfo] = geocode_nyc_address(r.street_address, r.city, r.state, r.zip)
    except ValueError:
        return Response(
            {
                "detail": "Non-NYC registrations are not supported at this time. Check back later, "
                "or email support@nycmesh.net"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except AddressError as e:
        return Response({"detail": e.args[0]}, status=status.HTTP_400_BAD_REQUEST)

    if not nyc_addr_info:
        return Response(
            {"detail": "Your address could not be validated."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Keep a blank JoinFormRequest to mutate with the info we've joined. We'll send it back
    # for their review if anything was changed by our validation.
    info_changed = False
    changed_info = JoinFormRequest(
        first_name="",
        last_name="",
        email="",
        phone=formatted_phone_number if formatted_phone_number != None and r.phone != formatted_phone_number else "",
        street_address=nyc_addr_info.street_address if r.street_address != nyc_addr_info.street_address else "",
        city=nyc_addr_info.city if r.city != nyc_addr_info.city else "",
        state=nyc_addr_info.state if r.state != nyc_addr_info.state else "",
        zip=nyc_addr_info.zip if r.zip != nyc_addr_info.zip else 0,
        apartment="",
        roof_access=False,
        referral="",
        ncl=False,
    )

    for field in changed_info.__dataclass_fields__:
        value = getattr(changed_info, field)
        if value != "" and value != 0 and value:
            info_changed = True
            print(f"Changed {field} ({value})")

    # Let the member know we need to confirm some info with them. This is not
    # a rejection. We expect another join form submission with all this info in 
    # place for us
    if info_changed:
        return Response(
            {
                "detail": "Please confirm a few details.",
                "building_id": None,
                "member_id": None,
                "install_id": None,
                "install_number": None,
                # If this is an existing member, then set a flag to let them know we have
                # their information in case they need to update anything.
                "member_exists": None,
                "info_changed": info_changed,
                "changed_info": JoinFormRequestSerializer(changed_info).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # Check if there's an existing member. Group members by matching on both email and phone
    # A member can have multiple install requests, if they move apartments for example
    existing_member_filter_criteria = []
    if r.email:
        existing_member_filter_criteria.append(
            Q(primary_email_address=r.email)
            | Q(stripe_email_address=r.email)
            | Q(additional_email_addresses__contains=[r.email])
        )

    if formatted_phone_number:
        existing_member_filter_criteria.append(
            Q(phone_number=formatted_phone_number) | Q(additional_phone_numbers=[formatted_phone_number])
        )

    existing_members = list(
        Member.objects.filter(
            reduce(
                operator.or_,
                existing_member_filter_criteria,
            )
        )
    )

    join_form_member = (
        existing_members[0]
        if len(existing_members) > 0
        else Member(
            name=join_form_full_name,
            primary_email_address=r.email,
            phone_number=formatted_phone_number,
            slack_handle=None,
        )
    )

    if r.email not in join_form_member.all_email_addresses:
        join_form_member.additional_email_addresses.append(r.email)

    if formatted_phone_number not in join_form_member.all_phone_numbers:
        join_form_member.additional_phone_numbers.append(formatted_phone_number)

    # Try to map this address to an existing Building or group of buildings
    all_existing_buildings_for_structure = Building.objects.filter(bin=nyc_addr_info.bin)
    existing_exact_buildings = all_existing_buildings_for_structure.filter(street_address=nyc_addr_info.street_address)

    existing_primary_nodes_for_structure = list(
        {building.primary_node for building in all_existing_buildings_for_structure}
    )
    existing_nodes_for_structure = {
        node for building in all_existing_buildings_for_structure for node in building.nodes.all()
    }

    if len(existing_exact_buildings) > 1:
        logging.warning(
            f"Found multiple buildings with BIN {nyc_addr_info.bin} and "
            f"address {nyc_addr_info.street_address} this should not happen, "
            f"and these should be consolidated"
        )

    if len(existing_primary_nodes_for_structure) > 1:
        logging.warning(
            f"Found multiple primary nodes for the cluster of nodes {existing_nodes_for_structure} "
            f"at address {nyc_addr_info.street_address}. This should not happen, "
            f"these should be consolidated"
        )

    join_form_building = (
        existing_exact_buildings[0]
        if len(existing_exact_buildings) > 0
        else Building(
            bin=nyc_addr_info.bin if nyc_addr_info is not None else None,
            street_address=nyc_addr_info.street_address,
            city=nyc_addr_info.city,
            state=nyc_addr_info.state,
            zip_code=int(nyc_addr_info.zip),
            latitude=nyc_addr_info.latitude,
            longitude=nyc_addr_info.longitude,
            altitude=nyc_addr_info.altitude,
            address_truth_sources=[AddressTruthSource.NYCPlanningLabs],
        )
    )

    if not join_form_building.primary_node:
        join_form_building.primary_node = (
            existing_primary_nodes_for_structure[0] if existing_primary_nodes_for_structure else None
        )

    join_form_install = Install(
        status=Install.InstallStatus.REQUEST_RECEIVED,
        ticket_number=None,
        request_date=date.today(),
        install_date=None,
        abandon_date=None,
        building=join_form_building,
        unit=r.apartment,
        roof_access=r.roof_access,
        member=join_form_member,
        referral=r.referral,
        notes=None,
        node=join_form_building.primary_node if join_form_building.primary_node else None,
    )

    try:
        join_form_member.save()
    except IntegrityError:
        logging.exception("Error saving member from join form")
        return Response(
            {"detail": "There was a problem saving your Member information"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        join_form_building.save()

        # If this building is a new building in a shared structure of buildings with
        # existing node(s), update the node-building relation to reflect the new building's
        # association with the existing nodes
        for node in existing_nodes_for_structure:
            join_form_building.nodes.add(node)
    except IntegrityError:
        logging.exception("Error saving building from join form")
        # Delete the member and bail
        join_form_member.delete()
        return Response(
            {"detail": "There was a problem saving your Building information"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        join_form_install.save()
    except IntegrityError:
        logging.exception("Error saving install from join form")
        # Delete the member, building (if we just created it), and bail
        join_form_member.delete()
        if len(existing_exact_buildings) == 0:
            join_form_building.delete()
        return Response(
            {"detail": "There was a problem saving your Install information"}, status=status.HTTP_400_BAD_REQUEST
        )

    if existing_members:
        if join_form_member.name != join_form_full_name:
            name_change_note = (
                f"Dropped name change: {join_form_full_name} (install request #{join_form_install.install_number})"
            )
            if join_form_member.notes:
                join_form_member.notes = join_form_member.notes.strip() + "\n" + name_change_note
            else:
                join_form_member.notes = name_change_note
            join_form_member.save()

            notify_administrators_of_data_issue(
                [join_form_member],
                MemberSerializer,
                name_change_note,
                request,
            )

        if len(existing_members) > 1:
            notify_administrators_of_data_issue(
                existing_members + [join_form_member],
                MemberSerializer,
                "Possible duplicate member objects detected",
                request,
            )

    logging.info(
        f"JoinForm submission success. building_id: {join_form_building.id}, "
        f"member_id: {join_form_member.id}, install_number: {join_form_install.install_number}"
    )

    return Response(
        {
            "detail": "Thanks! A volunteer will email you shortly",
            "building_id": join_form_building.id,
            "member_id": join_form_member.id,
            "install_id": join_form_install.id,
            "install_number": join_form_install.install_number,
            # If this is an existing member, then set a flag to let them know we have
            # their information in case they need to update anything.
            "member_exists": True if len(existing_members) > 0 else False,
            "info_changed": info_changed,
            "changed_info": JoinFormRequestSerializer(changed_info).data,
        },
        status=status.HTTP_201_CREATED,
    )


@dataclass
class NetworkNumberAssignmentRequest:
    install_number: int


class NetworkNumberAssignmentRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = NetworkNumberAssignmentRequest

    password = serializers.CharField()


nn_form_success_schema = inline_serializer(
    "NNFormSuccessResponse",
    fields={
        "detail": serializers.CharField(),
        "building_id": serializers.UUIDField(),
        "install_id": serializers.UUIDField(),
        "install_number": serializers.IntegerField(),
        "network_number": serializers.IntegerField(),
        "created": serializers.BooleanField(),
    },
)


@extend_schema_view(
    post=extend_schema(
        tags=["User Forms"],
        summary="Assign a network number to a given Install object. Used by the NN Assignment form",
        request=NetworkNumberAssignmentRequestSerializer,
        responses={
            "200": OpenApiResponse(
                nn_form_success_schema,
                description="This install already has an NN, no action has been perfomed in the DB",
            ),
            "201": OpenApiResponse(
                nn_form_success_schema,
                description="This install did not already have an NN. One has been found "
                "(either from the backlog of unused installs or already existing on the Building) "
                "and assigned to this install.",
            ),
            "400": OpenApiResponse(
                form_err_response_schema, description="Invalid request body JSON or missing required fields"
            ),
            "403": OpenApiResponse(form_err_response_schema, description="Incorrect or missing password"),
            "404": OpenApiResponse(form_err_response_schema, description="Requested install number could not be found"),
            "500": OpenApiResponse(form_err_response_schema, description="Unexpected internal error"),
        },
    ),
)
@api_view(["POST"])
@permission_classes([HasNNAssignPermission | LegacyNNAssignmentPassword])
@transaction.atomic
@advisory_lock("nn_assignment_lock")
def network_number_assignment(request: Request) -> Response:
    """
    Takes an install number, and assigns the install a network number,
    deduping using the other buildings in our database.
    """

    try:
        request_json = json.loads(request.body)
        if "password" in request_json:
            del request_json["password"]

        r = NetworkNumberAssignmentRequest(**request_json)
    except (TypeError, JSONDecodeError):
        logging.exception("NN Request failed. Could not decode request")
        return Response({"detail": "Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Here we use select_for_update() and select_related() to ensure we acquire a lock on all
        # rows related to the Install object at hand, so that for example, the attached building
        # isn't changed underneath us
        nn_install = Install.objects.select_for_update().select_related().get(install_number=r.install_number)
    except Exception:
        logging.exception(f'NN Request failed. Could not get Install w/ Install Number "{r.install_number}"')
        return Response({"detail": "Install Number not found"}, status=status.HTTP_404_NOT_FOUND)

    # Track if we have made any changes, so we know what status code to return
    dirty = False

    nn_building = nn_install.building

    # First, we try to identify a Node object for this install if it doesn't already have one
    if not nn_install.node:
        # If the building on this install has a primary_node, then use that one
        if nn_building.primary_node is not None:
            logging.info(f"Reusing existing node ({nn_building.primary_node.id}) from building ({nn_building.id})")
            nn_install.node = nn_building.primary_node
            dirty = True
        else:
            # Otherwise we need to build a new node from scratch
            nn_install.node = Node(
                status=Node.NodeStatus.PLANNED,
                latitude=nn_building.latitude,
                longitude=nn_building.longitude,
                altitude=nn_building.altitude,
                install_date=date.today(),
                notes="Created by NN Assignment form",
            )
            dirty = True
    else:
        logging.info(f"Reusing existing node ({nn_install.node.id}) already attached to install ({nn_install.id})")

    # Set the node on the Building (if needed)
    if not nn_building.primary_node:
        nn_building.primary_node = nn_install.node
        dirty = True

    # If the node we have attached does not have a network number, it's time to assign one
    if nn_install.node.network_number is None:
        # Try to use the install number if it is a valid number and unused
        #
        # We also don't use the install number if the install status indicates the number has been
        # re-used (even if it hasn't been according to the Node table). This shouldn't be common,
        # but NN assignment is critical, so we want to be defensive in the case of incongruent
        # database data. We could expand this list of "prohibited statuses" to align more closely
        # with the logic used to determine the lowest NN, but that would mean refusing to give low
        # installs their own (available) NN, just because the install was marked "pending". The
        # reason for this logic mismatch really is so that we _can_ use it here, (i.e. we  didn't
        # give their number out in get_next_available_network_number() because we are saving it
        # specifically for use on their install)
        candidate_nn = nn_install.install_number
        if (
            candidate_nn < NETWORK_NUMBER_MIN
            or candidate_nn > NETWORK_NUMBER_MAX
            or len(Node.objects.filter(network_number=candidate_nn))
            or nn_install.status in [Install.InstallStatus.NN_REASSIGNED, Install.InstallStatus.CLOSED]
        ):
            # If that doesn't work, lookup the lowest available number and use that
            try:
                candidate_nn = get_next_available_network_number()
            except ValueError as exception:
                return Response(
                    {"detail": f"NN Request failed. {exception.args[0]}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        nn_install.node.network_number = candidate_nn
        dirty = True

    # Mark the Install & node as planned (if needed)
    if nn_install.node.status == Node.NodeStatus.INACTIVE:
        nn_install.node.status = Node.NodeStatus.PLANNED
        dirty = True

    if nn_install.status == Install.InstallStatus.REQUEST_RECEIVED:
        nn_install.status = Install.InstallStatus.PENDING
        dirty = True

    # If nothing was changed by this request, return a 200 instead of a 201
    if not dirty:
        message = f"This Install Number ({r.install_number}) already has a "
        f"Network Number ({nn_install.node.network_number}) associated with it!"
        logging.warning(message)
        return Response(
            {
                "detail": message,
                "building_id": nn_install.building.id,
                "install_id": nn_install.id,
                "install_number": nn_install.install_number,
                "network_number": nn_install.node.network_number,
                "created": False,
            },
            status=status.HTTP_200_OK,
        )

    try:
        nn_install.node.save()
        nn_building.save()
        nn_install.save()
    except IntegrityError:
        logging.exception("NN Request failed. Could not save node number.")
        return Response(
            {"detail": "NN Request failed. Could not save node number."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "detail": "Network Number has been assigned!",
            "building_id": nn_building.id,
            "install_id": nn_install.id,
            "install_number": nn_install.install_number,
            "network_number": nn_install.node.network_number,
            "created": True,
        },
        status=status.HTTP_201_CREATED,
    )
