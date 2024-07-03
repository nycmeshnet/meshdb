from typing import Any, List, Type

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.models import Building, Device, Install, Link, Member, Node, Sector
from meshapi.serializers import (
    BuildingSerializer,
    DeviceSerializer,
    InstallSerializer,
    LinkSerializer,
    MemberSerializer,
    NodeSerializer,
    SectorSerializer,
)


class FilterRequiredListAPIView(generics.ListAPIView):
    filterset_class: Type[filters.FilterSet]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        possible_filters = set(self.filterset_class.get_filters().keys())  # type: ignore[no-untyped-call]
        provided_filters = set(self.request.query_params.keys())
        invalid_filters = provided_filters - possible_filters

        if not provided_filters:
            return Response({"detail": "Please provide at least one filter to use this endpoint"}, 400)

        # If they gave us filters that aren't actually available, bail and return a bad status
        if invalid_filters:
            return Response({"detail": f"Invalid filters provided: {list(invalid_filters)}"}, 400)

        return super().get(request, *args, **kwargs)


class MemberFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    email_address = filters.CharFilter(method="filter_on_all_emails")
    phone_number = filters.CharFilter(field_name="phone_number", lookup_expr="icontains")

    def filter_on_all_emails(self, queryset: QuerySet[Member], field_name: str, value: str) -> QuerySet[Member]:
        return queryset.filter(
            Q(primary_email_address__icontains=value)
            | Q(stripe_email_address__icontains=value)
            | Q(additional_email_addresses__icontains=value)
        )

    class Meta:
        model = Member
        fields: List[Any] = []


@extend_schema_view(
    get=extend_schema(
        tags=["Members"],
        parameters=[
            OpenApiParameter(
                "name",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by the name field using case-insensitve substring matching",
                required=False,
            ),
            OpenApiParameter(
                "email_address",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by any of the email address fields using case-insensitve "
                "substring matching",
                required=False,
            ),
            OpenApiParameter(
                "phone_number",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by the phone_number field using case-insensitve substring matching",
                required=False,
            ),
        ],
    ),
)
class LookupMember(FilterRequiredListAPIView):
    queryset = Member.objects.all().order_by("id")
    serializer_class = MemberSerializer
    filterset_class = MemberFilter


class InstallFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="node__network_number", lookup_expr="exact")

    class Meta:
        model = Install
        fields = ["member", "building", "status"]


@extend_schema_view(
    get=extend_schema(
        tags=["Installs"],
        parameters=[
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by network_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "member",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by the Member id foreign key field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "building",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by the Building id foreign key field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the status field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupInstall(FilterRequiredListAPIView):
    queryset = Install.objects.all().order_by("install_number")
    serializer_class = InstallSerializer
    filterset_class = InstallFilter


class BuildingFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="nodes__network_number", lookup_expr="exact")
    primary_network_number = filters.NumberFilter(field_name="primary_node", lookup_expr="exact")
    install_number = filters.NumberFilter(field_name="installs__install_number", lookup_expr="exact")
    street_address = filters.CharFilter(field_name="street_address", lookup_expr="icontains")
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    state = filters.CharFilter(field_name="state", lookup_expr="iexact")

    class Meta:
        model = Building
        fields = ["bin", "zip_code"]


@extend_schema_view(
    get=extend_schema(
        tags=["Buildings"],
        parameters=[
            OpenApiParameter(
                "install_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter Buildings by install_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter Buildings by the network number of their associated nodes using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "primary_network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter Buildings by the network number of their primary node using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "bin",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by bin using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "street_address",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the street_address field using case-insensitve substring matching",
                required=False,
            ),
            OpenApiParameter(
                "city",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the city field using case-insensitve equality",
                required=False,
            ),
            OpenApiParameter(
                "state",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the state field using case-insensitve equality",
                required=False,
            ),
            OpenApiParameter(
                "zip_code",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the zip_code field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupBuilding(FilterRequiredListAPIView):
    queryset = Building.objects.all().order_by("id")
    serializer_class = BuildingSerializer
    filterset_class = BuildingFilter


class NodeFilter(filters.FilterSet):
    install_number = filters.NumberFilter(field_name="installs__install_number", lookup_expr="exact")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    building = filters.NumberFilter(field_name="buildings", lookup_expr="exact")

    class Meta:
        model = Node
        fields = ["status"]


@extend_schema_view(
    get=extend_schema(
        tags=["Nodes"],
        parameters=[
            OpenApiParameter(
                "name",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter nodes by the name field using case-insensitve substring matching",
                required=False,
            ),
            OpenApiParameter(
                "install_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter nodes by install_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "building",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter nodes by the Building id foreign key field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter nodes by the status field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupNode(FilterRequiredListAPIView):
    queryset = Node.objects.all().order_by("network_number")
    serializer_class = NodeSerializer
    filterset_class = NodeFilter


class LinkFilter(filters.FilterSet):
    network_number = filters.NumberFilter(method="filter_from_to_network_number")
    device = filters.NumberFilter(method="filter_from_to_device_id")

    def filter_from_to_network_number(self, queryset: QuerySet[Link], field_name: str, value: str) -> QuerySet[Link]:
        return queryset.filter(Q(from_device__node__network_number=value) | Q(to_device__node__network_number=value))

    def filter_from_to_device_id(self, queryset: QuerySet[Link], field_name: str, value: str) -> QuerySet[Link]:
        return queryset.filter(Q(from_device__id=value) | Q(to_device__id=value))

    class Meta:
        model = Link
        fields = ["status", "type", "uisp_id"]


@extend_schema_view(
    get=extend_schema(
        tags=["Links"],
        parameters=[
            OpenApiParameter(
                "device",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter links by the id of the devices they connect using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter links by network_number of the devices they connect using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "type",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter links by the type field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter links by the status field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "uisp_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter links by the uisp_id field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupLink(FilterRequiredListAPIView):
    queryset = Link.objects.all().order_by("id")
    serializer_class = LinkSerializer
    filterset_class = LinkFilter


class DeviceFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="node", lookup_expr="exact")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Device
        fields = ["type", "status", "model", "uisp_id", "ssid"]


@extend_schema_view(
    get=extend_schema(
        tags=["Devices"],
        parameters=[
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter devices by network_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "type",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the type field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the status field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "model",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the model name field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "uisp_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the uisp_id field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "ssid",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the ssid field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "name",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter devices by the name field using case-insensitve substring matching",
                required=False,
            ),
        ],
    ),
)
class LookupDevice(FilterRequiredListAPIView):
    queryset = Device.objects.all().order_by("id")
    serializer_class = DeviceSerializer
    filterset_class = DeviceFilter


class SectorFilter(DeviceFilter):
    class Meta:
        model = Sector
        fields = DeviceFilter.Meta.fields


@extend_schema_view(
    get=extend_schema(
        tags=["Sectors"],
        parameters=[
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter sectors by network_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "type",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the type field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the status field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "model",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the model name field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "uisp_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the uisp_id field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "ssid",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the ssid field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "name",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter sectors by the name field using case-insensitve substring matching",
                required=False,
            ),
        ],
    ),
)
class LookupSector(FilterRequiredListAPIView):
    queryset = Sector.objects.all().order_by("id")
    serializer_class = SectorSerializer
    filterset_class = SectorFilter
