from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Member, Node, Sector
from meshapi.serializers import (
    AccessPointSerializer,
    BuildingSerializer,
    DeviceSerializer,
    InstallSerializer,
    LinkSerializer,
    LOSSerializer,
    MemberSerializer,
    NodeSerializer,
    SectorSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["API Status"],
        responses=OpenApiResponse(
            description="API is up and serving traffic",
            response=OpenApiTypes.STR,
            examples=[OpenApiExample(name="Default", value="We're meshin'.")],
        ),
        auth=[],
        summary="Check API status",
    ),
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_root(request: Request, format: Any = None) -> Response:
    """
    This endpoint can be used by clients to determine the health status of this API. This API always
    returns 200 status codes, accepts no input, and has no side effects. It always returns the
    string "We're meshin'."
    """
    return Response("We're meshin'.")


@extend_schema_view(
    get=extend_schema(tags=["Buildings"]),
    post=extend_schema(tags=["Buildings"]),
)
class BuildingList(generics.ListCreateAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


@extend_schema_view(
    get=extend_schema(tags=["Buildings"]),
    put=extend_schema(tags=["Buildings"]),
    patch=extend_schema(tags=["Buildings"]),
    delete=extend_schema(tags=["Buildings"]),
)
class BuildingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


@extend_schema_view(
    get=extend_schema(tags=["Members"]),
    post=extend_schema(tags=["Members"]),
)
class MemberList(generics.ListCreateAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


@extend_schema_view(
    get=extend_schema(tags=["Members"]),
    put=extend_schema(tags=["Members"]),
    patch=extend_schema(tags=["Members"]),
    delete=extend_schema(tags=["Members"]),
)
class MemberDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


@extend_schema_view(
    get=extend_schema(tags=["Installs"]),
    post=extend_schema(tags=["Installs"]),
)
class InstallList(generics.ListCreateAPIView):
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


@extend_schema_view(
    get=extend_schema(tags=["Installs"]),
    put=extend_schema(tags=["Installs"]),
    patch=extend_schema(tags=["Installs"]),
    delete=extend_schema(tags=["Installs"]),
)
class InstallDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Install.objects.all()
    serializer_class = InstallSerializer


@extend_schema_view(
    get=extend_schema(tags=["Nodes"]),
    post=extend_schema(tags=["Nodes"]),
)
class NodeList(generics.ListCreateAPIView):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer


@extend_schema_view(
    get=extend_schema(tags=["Nodes"]),
    put=extend_schema(tags=["Nodes"]),
    patch=extend_schema(tags=["Nodes"]),
    delete=extend_schema(tags=["Nodes"]),
)
class NodeDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer


@extend_schema_view(
    get=extend_schema(tags=["Links"]),
    post=extend_schema(tags=["Links"]),
)
class LinkList(generics.ListCreateAPIView):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer


@extend_schema_view(
    get=extend_schema(tags=["Links"]),
    put=extend_schema(tags=["Links"]),
    patch=extend_schema(tags=["Links"]),
    delete=extend_schema(tags=["Links"]),
)
class LinkDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer


@extend_schema_view(
    get=extend_schema(tags=["LOSes"]),
    post=extend_schema(tags=["LOSes"]),
)
class LOSList(generics.ListCreateAPIView):
    queryset = LOS.objects.all()
    serializer_class = LOSSerializer


@extend_schema_view(
    get=extend_schema(tags=["LOSes"]),
    put=extend_schema(tags=["LOSes"]),
    patch=extend_schema(tags=["LOSes"]),
    delete=extend_schema(tags=["LOSes"]),
)
class LOSDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = LOS.objects.all()
    serializer_class = LOSSerializer


@extend_schema_view(
    get=extend_schema(tags=["Devices"]),
    post=extend_schema(tags=["Devices"]),
)
class DeviceList(generics.ListCreateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


@extend_schema_view(
    get=extend_schema(tags=["Devices"]),
    put=extend_schema(tags=["Devices"]),
    patch=extend_schema(tags=["Devices"]),
    delete=extend_schema(tags=["Devices"]),
)
class DeviceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


@extend_schema_view(
    get=extend_schema(tags=["Sectors"]),
    post=extend_schema(tags=["Sectors"]),
)
class SectorList(generics.ListCreateAPIView):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


@extend_schema_view(
    get=extend_schema(tags=["Sectors"]),
    put=extend_schema(tags=["Sectors"]),
    patch=extend_schema(tags=["Sectors"]),
    delete=extend_schema(tags=["Sectors"]),
)
class SectorDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


@extend_schema_view(
    get=extend_schema(tags=["AccessPoints"]),
    post=extend_schema(tags=["AccessPoints"]),
)
class AccessPointList(generics.ListCreateAPIView):
    queryset = AccessPoint.objects.all()
    serializer_class = AccessPointSerializer


@extend_schema_view(
    get=extend_schema(tags=["AccessPoints"]),
    put=extend_schema(tags=["AccessPoints"]),
    patch=extend_schema(tags=["AccessPoints"]),
    delete=extend_schema(tags=["AccessPoints"]),
)
class AccessPointDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AccessPoint.objects.all()
    serializer_class = AccessPointSerializer
