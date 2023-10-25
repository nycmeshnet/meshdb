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
from validate_email import validate_email
import phonenumbers
from geopy.geocoders import Nominatim


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

    expected_structure = {
        "first_name": str,
        "last_name": str,
        "email": str,
        "phone": str,
        "street_address": str,
        "city": str,
        "state": str,
        "zip": int,
        "apartment": str,
        "roof_access": bool,
        "referral": str,
    }

    for key, expected_type in expected_structure.items():
        if key not in request_json:
            print(f"Missing key: {key}")
            return Response({f"Missing key: {key}"}, status=status.HTTP_400_BAD_REQUEST)
        elif not isinstance(request_json[key], expected_type):
            print(
                f"Key '{key}' has an incorrect data type. Expected {expected_type}, but got {type(request_json[key])}"
            )
            return Response(
                {
                    f"Key '{key}' has an incorrect data type. Expected {expected_type}, but got {type(request_json[key])}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    first_name: str = request_json.get("first_name")
    last_name: str = request_json.get("last_name")
    email_address: str = request_json.get("email")
    phone_number: str = request_json.get("phone")
    street_address: str = request_json.get("street_address")
    apartment: str = request_json.get("apartment")
    roof_access: bool = request_json.get("roof_access")
    city: str = request_json.get("city")
    state: str = request_json.get("state")
    zip_code: str = request_json.get("zip")
    referral: str = request_json.get("referral")

    # TODO: Formatting validation? Email, Phone, yada yada.
    # FIXME (willnilges): No smtp?
    print("Validating Email...")
    if not validate_email(
        email_address=email_address,
        check_format=True,
        check_blacklist=True,
        check_dns=True,
        dns_timeout=5,
        check_smtp=False,
    ):
        return Response({f"{email_address} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)

    # Expects country code!!!!
    print("Validating Phone...")
    try:
        phonenumbers.parse(phone_number, None)
    except phonenumbers.NumberParseException:
        return Response({f"{phone_number} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    # FIXME (willnilges): OSM apparently doesn't have altitude data
    # (https://geopy.readthedocs.io/en/latest/index.html?highlight=Altitude#geopy.location.Location.altitude)
    try:
        print("Validating Address...")
        geolocator = Nominatim(user_agent="address_lookup")
        address = f"{street_address}, {city}, {state} {zip_code}"
        location = geolocator.geocode(address)
        # TODO: We need a log library, because I want to be able to turn on
        # debug logs for tests and debugging
        print(f"Location is: {location}")
        print(f"Latitude is: {location.latitude}")
        print(f"Longitude is: {location.longitude}")
        print(f"Altitude is: {location.altitude}")
        if location is None:
            raise ValueError()
    except Exception as e:
        print(e)
        return Response(f"Error parsing address.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    existing_members = Member.objects.filter(
        first_name=first_name,
        last_name=last_name,
        email_address=email_address,
        phone_number=phone_number,
    )

    if len(existing_members) > 0:
        return Response({"Member already exists"}, status=status.HTTP_400_BAD_REQUEST)

    join_form_member = Member(
        first_name=first_name,
        last_name=last_name,
        email_address=email_address,
        phone_number=phone_number,
        slack_handle="",
    )

    try:
        join_form_member.save()
    except IntegrityError as e:
        print(e)
        return Response({"Could not save member."}, status=status.HTTP_400_BAD_REQUEST)

    existing_buildings = Building.objects.filter(
        street_address=street_address,
        city=city,
        state=state,
        zip_code=zip_code,
    )

    # TODO: Implement BIN lookup, lat/long, and altitude
    join_form_building = (
        existing_buildings[0]
        if len(existing_buildings) > 0
        else Building(
            bin=69,
            building_status=Building.BuildingStatus.INACTIVE,
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=location.latitude,
            longitude=location.longitude,
            altitude=location.altitude,
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
        roof_access=roof_access,
        referral=referral,
        ticket_id=None,
        member_id=join_form_member,
        building_id=join_form_building,
        unit=apartment,
        install_id=None,
    )

    try:
        join_form_request.save()
    except IntegrityError as e:
        print(e)
        return Response({"Could not save request"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({}, status=status.HTTP_201_CREATED)
