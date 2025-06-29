import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from json.decoder import JSONDecodeError
from typing import Optional

from datadog import statsd
from ddtrace import tracer
from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from ipware import get_client_ip
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_dataclasses.serializers import DataclassSerializer
from validate_email.exceptions import EmailValidationError

from meshapi.exceptions import AddressError
from meshapi.models import AddressTruthSource, Building, Install, Member, Node
from meshapi.permissions import HasNNAssignPermission, LegacyNNAssignmentPassword
from meshapi.serializers import MemberSerializer
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.constants import INVALID_ALTITUDE, RECAPTCHA_CHECKBOX_TOKEN_HEADER, RECAPTCHA_INVISIBLE_TOKEN_HEADER
from meshapi.util.django_pglocks import advisory_lock
from meshapi.util.network_number import NETWORK_NUMBER_ASSIGN_MIN, NETWORK_NUMBER_MAX, get_next_available_network_number
from meshapi.validation import (
    NYCAddressInfo,
    geocode_nyc_address,
    normalize_phone_number,
    validate_email_address,
    validate_phone_number,
    validate_recaptcha_tokens,
)

logging.basicConfig()

DISABLE_RECAPTCHA_VALIDATION = os.environ.get("RECAPTCHA_DISABLE_VALIDATION", "").lower() == "true"


# Join Form
@dataclass
class JoinFormRequest:
    first_name: str
    last_name: str
    email_address: str
    phone_number: str
    street_address: str
    city: str
    state: str
    zip_code: str
    apartment: str
    roof_access: bool
    referral: str
    ncl: bool
    trust_me_bro: bool  # Used to override member data correction


class JoinFormRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = JoinFormRequest


form_err_response_schema = inline_serializer("ErrorResponse", fields={"detail": serializers.CharField()})


@tracer.wrap()
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
                        "changed_info": serializers.DictField(),
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
    statsd.increment("meshdb.join_form.request", tags=[])
    request_json = json.loads(request.body)
    try:
        r = JoinFormRequest(**request_json)
    except TypeError:
        logging.exception("TypeError while processing JoinForm")
        return Response({"detail": "Got incomplete form request"}, status=status.HTTP_400_BAD_REQUEST)

    if not DISABLE_RECAPTCHA_VALIDATION:
        try:
            request_source_ip, request_source_ip_is_routable = get_client_ip(request)
            if not request_source_ip_is_routable:
                request_source_ip = None

            recaptcha_invisible_token = request.headers.get(RECAPTCHA_INVISIBLE_TOKEN_HEADER)
            if recaptcha_invisible_token == "":
                recaptcha_invisible_token = None

            recaptcha_checkbox_token = request.headers.get(RECAPTCHA_CHECKBOX_TOKEN_HEADER)
            if recaptcha_checkbox_token == "":
                recaptcha_checkbox_token = None

            validate_recaptcha_tokens(recaptcha_invisible_token, recaptcha_checkbox_token, request_source_ip)
        except Exception:
            logging.exception("Captcha validation failed")
            return Response({"detail": "Captcha verification failed"}, status=status.HTTP_401_UNAUTHORIZED)

    response = process_join_form(r, request)
    statsd.increment("meshdb.join_form.response", tags=[f"status:{response.status_code}"])
    return response


def process_join_form(r: JoinFormRequest, request: Optional[Request] = None) -> Response:
    if not r.ncl:
        return Response(
            {"detail": "You must agree to the Network Commons License!"}, status=status.HTTP_400_BAD_REQUEST
        )

    join_form_full_name = f"{r.first_name} {r.last_name}"

    if not r.email_address:
        return Response({"detail": "Must provide an email"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if r.email_address and not validate_email_address(r.email_address):
            return Response({"detail": f"{r.email_address} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)
    except EmailValidationError:
        # DNSTimeoutError, SMTPCommunicationError, and TLSNegotiationError are all subclasses of EmailValidationError.
        # Any other EmailValidationError will be caught inside validate_email_address() and trigger a return false,
        # so we know that if validate_email_address() throws, EmailValidationError, it must be one of these
        # and therefore our fault
        return Response(
            {"detail": "Could not validate email address due to an internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Expects country code!!!!
    if r.phone_number and not validate_phone_number(r.phone_number):
        return Response({"detail": f"{r.phone_number} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    formatted_phone_number = normalize_phone_number(r.phone_number) if r.phone_number else None

    try:
        try:
            nyc_addr_info: Optional[NYCAddressInfo] = geocode_nyc_address(r.street_address, r.city, r.state, r.zip_code)
        except Exception as e:
            # Ensure this gets logged
            logging.exception(e)
            raise e
    except ValueError:
        logging.debug(r.street_address, r.city, r.state, r.zip_code)
        return Response(
            {
                "detail": "Non-NYC registrations are not supported at this time. Please double check your zip code, "
                "or send an email to support@nycmesh.net"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except AddressError as e:
        return Response({"detail": e.args[0]}, status=status.HTTP_400_BAD_REQUEST)

    if not nyc_addr_info:
        return Response(
            {"detail": "Your address could not be validated."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    changed_info: dict[str, str | int] = {}

    if formatted_phone_number and r.phone_number != formatted_phone_number:
        logging.warning(f"Changed phone_number: {formatted_phone_number} != {r.phone_number}")
        changed_info["phone_number"] = formatted_phone_number

    if r.street_address != nyc_addr_info.street_address:
        logging.warning(f"Changed street_address: {r.street_address} != {nyc_addr_info.street_address}")
        changed_info["street_address"] = nyc_addr_info.street_address

    if r.city != nyc_addr_info.city:
        logging.warning(f"Changed city: {r.city} != {nyc_addr_info.city}")
        changed_info["city"] = nyc_addr_info.city

    # Let the member know we need to confirm some info with them. We'll send
    # back a dictionary with the info that needs confirming.
    # This is not a rejection. We expect another join form submission with all
    # of this info in place for us.
    if changed_info:
        if r.trust_me_bro:
            logging.warning(
                "Got trust_me_bro, even though info was still updated "
                f"(email: {r.email_address}, changed_info: {changed_info}). "
                "Proceeding with install request submission."
            )
            nyc_addr_info.street_address = r.street_address
            nyc_addr_info.city = r.city
            nyc_addr_info.state = r.state
            nyc_addr_info.zip = r.zip_code
            nyc_addr_info.longitude = 0.0
            nyc_addr_info.latitude = 0.0
            nyc_addr_info.altitude = INVALID_ALTITUDE
            nyc_addr_info.bin = None

            formatted_phone_number = r.phone_number

        else:
            logging.warning("Please confirm a few details")
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
                    "changed_info": changed_info,
                },
                status=status.HTTP_409_CONFLICT,
            )

    # A member can have multiple install requests, if they move apartments for example, so we
    # check if there's an existing member. Group members by matching only on primary email address
    # This is sublte but important. We do NOT want to dedupe on phone number, or even on additional
    # email addresses at this time because this could lead to a situation where the email address
    # entered in the join form does not match the email address we send the OSTicket to.
    #
    # That seems like a minor problem, but is actually a potential safety risk. Consider the case
    # where a couple uses one person's email address to fill out the join form, but signs up for
    # stripe payments with the other person's email address. If they then break up, and one person
    # moves out, we definitely do not want to send an email with their new home address to their ex
    existing_members = list(Member.objects.filter(Q(primary_email_address=r.email_address)))

    join_form_member = (
        existing_members[0]
        if len(existing_members) > 0
        else Member(
            name=join_form_full_name,
            primary_email_address=r.email_address,
            phone_number=formatted_phone_number,
            slack_handle=None,
        )
    )

    if r.email_address not in join_form_member.all_email_addresses:
        join_form_member.additional_email_addresses.append(r.email_address)

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
            zip_code=nyc_addr_info.zip,
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

    existing_install = Install.objects.filter(
        building=join_form_building,
        member=join_form_member,
        unit__exact=r.apartment,
        # We only recycle install objects if nothing special has happened to them,
        # if they're not REQUEST_RECEIVED, that dramatically increases the chance that
        # a new identifier is warranted. e.g. NN_REASSIGNED indicates that's an absolute must
        status=Install.InstallStatus.REQUEST_RECEIVED,
    ).first()
    if existing_install:
        logging.warning(
            f"Discarding join form submission because an install was found with exactly "
            f"matching information: #{existing_install.install_number}"
        )
        return Response(
            {
                "detail": "Thanks! A volunteer will email you shortly",
                "building_id": join_form_building.id,
                "member_id": join_form_member.id,
                "install_id": existing_install.id,
                "install_number": existing_install.install_number,
                "member_exists": True,
                "changed_info": {},
            },
            status=status.HTTP_200_OK,
        )

    join_form_install = Install(
        status=Install.InstallStatus.REQUEST_RECEIVED,
        ticket_number=None,
        request_date=datetime.now(timezone.utc),
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
        if r.trust_me_bro:
            join_form_member.save_without_phone_number_validation()
        else:
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
        if join_form_member.name.lower() != join_form_full_name.lower():
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

    success_message = f"""JoinForm submission success {"(changed_info)" if changed_info else ""} {"(trust_me_bro)" if r.trust_me_bro else ""}. \
building_id: {join_form_building.id}, member_id: {join_form_member.id}, \
install_number: {join_form_install.install_number}"""

    if r.trust_me_bro:
        logging.warning(success_message)
    else:
        logging.info(success_message)

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
            "changed_info": {},
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
            "409": OpenApiResponse(form_err_response_schema, description="Requested install is in an invalid state"),
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
        # Don't allow old recycled or closed installs to have a network number assigned to them,
        # since this would be very confusing. Installs in this status should re-submit the join
        # form and try again with a new install number
        if nn_install.status in [Install.InstallStatus.CLOSED, Install.InstallStatus.NN_REASSIGNED]:
            return Response(
                {
                    "detail": "Invalid install status for NN Assignment. "
                    "Re-submit the join form to create a new install number"
                },
                status=status.HTTP_409_CONFLICT,
            )

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
            candidate_nn < NETWORK_NUMBER_ASSIGN_MIN
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
