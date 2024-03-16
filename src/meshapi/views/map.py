from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions

from meshapi.models import Building, Device, Install, Link, Node, Sector
from meshapi.serializers import (
    ALLOWED_INSTALL_STATUSES,
    EXCLUDED_INSTALL_STATUSES,
    MapDataInstallSerializer,
    MapDataLinkSerializer,
    MapDataSectorSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary='Complete list of all "Nodes" (mostly Installs with some fake installs generated to solve NN re-use), '
        "unpaginated, in the format expected by the website map. (Warning: This endpoint is a legacy format and may be "
        "deprecated/removed in the future)",
    ),
)
class MapDataNodeList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataInstallSerializer
    pagination_class = None

    def get_queryset(self):
        all_installs = []

        queryset = Install.objects.filter(~Q(status__in=EXCLUDED_INSTALL_STATUSES))

        for install in queryset:
            all_installs.append(install)

        # We need to make sure there is an entry on the map for every NN, and since we excluded the
        # NN assigned rows in the query above, we need to go through the Node objects and
        # include the nns we haven't already covered via install num
        covered_nns = {
            install.install_number
            for install in all_installs
            if install.node and install.install_number == install.node.network_number
        }
        for node in Node.objects.filter(
            ~Q(status=Node.NodeStatus.INACTIVE) & Q(installs__status__in=ALLOWED_INSTALL_STATUSES)
        ):
            if node.network_number not in covered_nns:
                # Arbitrarily pick a representative install for the details of the "Fake" node
                representative_install = node.installs.all()[0]
                all_installs.append(
                    Install(
                        install_number=node.network_number,
                        status=Install.InstallStatus.NN_REASSIGNED,
                        building=representative_install.building,
                        request_date=representative_install.request_date,
                        roof_access=representative_install.roof_access,
                    ),
                )
                covered_nns.add(node.network_number)

        all_installs.sort(key=lambda i: i.install_number)
        return all_installs


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary="Complete list of all Links, unpaginated, in the format expected by the website map. "
        "(Warning: This endpoint is a legacy format and may be deprecated/removed in the future)",
    ),
)
class MapDataLinkList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataLinkSerializer
    pagination_class = None
    queryset = (
        Link.objects.exclude(status__in=[Link.LinkStatus.INACTIVE])
        .exclude(to_device__node__status=Node.NodeStatus.INACTIVE)
        .exclude(from_device__node__status=Node.NodeStatus.INACTIVE)
        # TODO: Possibly re-enable the below filters? They make make the map arguably more accurate,
        #  but less consistent with the current one by removing links between devices that are
        #  inactive in UISP
        # .exclude(from_device__status=Device.DeviceStatus.INACTIVE)
        # .exclude(to_device__status=Device.DeviceStatus.INACTIVE)
    )


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary="Complete list of all Sectors, unpaginated, in the format expected by the website map. "
        "(Warning: This endpoint is a legacy format and may be deprecated/removed in the future)",
    ),
)
class MapDataSectorList(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MapDataSectorSerializer
    pagination_class = None
    queryset = Sector.objects.filter(~Q(status__in=[Device.DeviceStatus.INACTIVE]))
