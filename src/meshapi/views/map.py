import logging
import uuid
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any, Dict, List

import requests
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, Subquery
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import generics, permissions, serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from meshapi.models import LOS, AccessPoint, Building, Device, Install, Link, Node, Sector
from meshapi.serializers import (
    EXCLUDED_INSTALL_STATUSES,
    MapDataInstallSerializer,
    MapDataLinkSerializer,
    MapDataSectorSerializer,
)

LINKNYC_KIOSK_DATA_URL = "https://data.cityofnewyork.us/resource/s4kf-3yrf.json?$limit=100000"

LINKNYC_KIOSK_STATUS_TRANSLATION = {
    "Live": "active",
    "Ready for Activation": "pending",
    "Installed": "installed",
}


def convert_access_point_id_to_fake_node_number(access_point_id: uuid.UUID) -> int:
    # Hacky, but we have no choice, we need this to present as a "node" object to the
    # map frontend and not conflict with any existing installs
    return 1_000_000 + (access_point_id.int % 1_000_000)


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

    def get_queryset(self) -> List[Install]:  # type: ignore[override]
        all_installs = []

        queryset = (
            Install.objects.select_related("building")
            .select_related("node")
            .prefetch_related("node__installs")
            .prefetch_related("node__devices")
            .filter(~Q(status__in=EXCLUDED_INSTALL_STATUSES))
        )

        for install in queryset:
            all_installs.append(install)

        # We need to make sure there is an entry on the map for every NN, and since we excluded the
        # NN assigned rows in the query above, we need to go through the Node objects and
        # include the nns we haven't already covered via install num
        covered_nns = {install.install_number for install in all_installs}
        for node in (
            Node.objects.filter(~Q(status=Node.NodeStatus.INACTIVE))
            .prefetch_related("devices")
            .prefetch_related("installs")
            .prefetch_related("buildings")
            .prefetch_related(
                Prefetch(
                    "installs",
                    queryset=Install.objects.all().select_related("building"),
                    to_attr="prefetched_installs",
                )
            )
            .prefetch_related(
                Prefetch(
                    "installs",
                    queryset=Install.objects.filter(status=Install.InstallStatus.ACTIVE).select_related("building"),
                    to_attr="active_installs",
                )
            )
        ):
            if node.network_number and node.network_number not in covered_nns:
                # Arbitrarily pick a representative install for the details of the "Fake" node,
                # preferring active installs if possible
                try:
                    representative_install = (
                        node.active_installs  # type: ignore[attr-defined]
                        or node.prefetched_installs  # type: ignore[attr-defined]
                    )[0]
                except IndexError:
                    representative_install = None

                if representative_install:
                    building = representative_install.building
                else:
                    building = node.buildings.first()

                if not building:
                    # If we couldn't get a building from the install or node,
                    # make a faux one instead, to carry the lat/lon info into the serializer
                    building = Building(
                        latitude=node.latitude,
                        longitude=node.longitude,
                        altitude=node.altitude,
                    )

                all_installs.append(
                    Install(
                        install_number=node.network_number,
                        node=node,
                        status=Install.InstallStatus.NN_REASSIGNED
                        if node.status == node.NodeStatus.ACTIVE
                        else Install.InstallStatus.REQUEST_RECEIVED,
                        building=building,
                        request_date=representative_install.request_date
                        if representative_install
                        else node.install_date,
                        roof_access=representative_install.roof_access if representative_install else True,
                    ),
                )
                covered_nns.add(node.network_number)

        all_installs.sort(key=lambda i: i.install_number)
        return all_installs

    def list(self, request: Request, *args: List[Any], **kwargs: Dict[str, Any]) -> Response:
        response = super().list(request, args, kwargs)

        # FIXME (wdn): I think I should make datetimes like this: x = datetime.now().astimezone(timezone.utc)
        # That I don't is probably why I get this error
        # RuntimeWarning: DateTimeField HistoricalInstall.request_date received a naive datetime (2024-11-22 22:52:36.755801) while time zone support is active.

        access_points = []
        for ap in AccessPoint.objects.filter(Q(status=Device.DeviceStatus.ACTIVE)):
            install_date = (
                int(
                    datetime.combine(
                        ap.install_date,
                        datetime.min.time(),
                    ).timestamp()
                    * 1000
                )
                if ap.install_date
                else None
            )
            ap_json = {
                "id": convert_access_point_id_to_fake_node_number(ap.id),
                "name": ap.name,
                "status": "Installed",
                "coordinates": [ap.longitude, ap.latitude, None],
                "roofAccess": False,
                "notes": "AP",
                "panoramas": [],
            }

            if install_date:
                ap_json["requestDate"] = install_date
                ap_json["installDate"] = install_date

            access_points.append(ap_json)

        response.data.extend(access_points)

        return response


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
        .prefetch_related("to_device__node")
        .prefetch_related("from_device__node")
        .filter(
            Q(  # This horrible monster query exists to de-duplicate links between the same node pairs
                # so that the map doesn't freak out. These often exist because different devices on
                # the same nodes can be linked. This deduplication happens somewhat arbitrarily
                # and is borrowed from https://stackoverflow.com/a/69938289
                pk__in=Link.objects.values("from_device__node__network_number", "to_device__node__network_number")
                .distinct()
                .annotate(
                    pk=Subquery(
                        Link.objects.filter(
                            from_device__node__network_number=OuterRef("from_device__node__network_number"),
                            to_device__node__network_number=OuterRef("to_device__node__network_number"),
                        )
                        .order_by("pk")
                        .values("pk")[:1]
                    )
                )
                .values_list("pk", flat=True)
            )
            | Q(from_device__node__network_number__isnull=True)
            | Q(to_device__node__network_number__isnull=True)
        )
        .order_by("from_device__node__network_number", "to_device__node__network_number")
        # TODO: Possibly re-enable the below filters? They make make the map arguably more accurate,
        #  but less consistent with the current one by removing links between devices that are
        #  inactive in UISP
        #  https://github.com/nycmeshnet/meshdb/issues/521
        # .exclude(from_device__status=Device.DeviceStatus.INACTIVE)
        # .exclude(to_device__status=Device.DeviceStatus.INACTIVE)
    )

    def list(self, request: Request, *args: List[Any], **kwargs: Dict[str, Any]) -> Response:
        response = super().list(request, *args, **kwargs)

        covered_links = {(link["from"], link["to"]) for link in response.data}

        # Slightly hacky way to show ethernet cable runs on the old map.
        # We just look for nodes where there are installs on separate buildings
        # and add fake link objects to connect the installs on those other buildings to
        # the node dot
        cable_runs = []

        for node in (
            Node.objects.annotate(num_buildings=Count("buildings"))
            .filter(num_buildings__gt=1)
            .filter(buildings__nodes__network_number__isnull=False)
            .exclude(status=Node.NodeStatus.INACTIVE)
            .prefetch_related(
                Prefetch(
                    "buildings__installs",
                    queryset=Install.objects.order_by("install_number").filter(status=Install.InstallStatus.ACTIVE),
                    to_attr="active_installs",
                )
            )
            .order_by("network_number")
        ):
            for building in node.buildings.all():
                active_installs = building.active_installs  # type: ignore[attr-defined]
                if active_installs:
                    from_install = active_installs[0].install_number
                    if from_install != node.network_number:
                        if (from_install, node.network_number) not in covered_links:
                            cable_runs.append(
                                {
                                    "from": from_install,
                                    "to": node.network_number,
                                    "status": "active",
                                }
                            )

        response.data.extend(cable_runs)

        # Since the old school map has no concept of a LOS, only potential Links, we need to
        # create a fake potential Link object to represent each of our LOS entries
        # For our purposes here, we only care about LOS entries between buildings that have
        # install numbers. If one side of an LOS is a building that has no installs associated with
        # it, we exclude it
        los_objects_with_installs = (
            LOS.objects.filter(
                Exists(Install.objects.filter(building=OuterRef("from_building")))
                & Exists(Install.objects.filter(building=OuterRef("to_building")))
                & ~Q(from_building=F("to_building"))
            )
            .exclude(
                # Remove any LOS objects that would duplicate Link objects,
                # to avoid cluttering the map
                Exists(
                    Link.objects.filter(
                        (
                            Q(from_device__node__buildings=OuterRef("from_building"))
                            & Q(to_device__node__buildings=OuterRef("to_building"))
                        )
                        | (
                            Q(from_device__node__buildings=OuterRef("to_building"))
                            & Q(to_device__node__buildings=OuterRef("from_building"))
                        )
                    )
                )
            )
            .filter(
                # This horrible monster query exists to de-duplicate LOSes between the same building
                # pairs so that the map doesn't freak out. This deduplication happens somewhat
                # arbitrarily and is borrowed from https://stackoverflow.com/a/69938289
                pk__in=LOS.objects.values("from_building", "to_building")
                .distinct()
                .annotate(
                    pk=Subquery(
                        LOS.objects.filter(
                            from_building=OuterRef("from_building"),
                            to_building=OuterRef("to_building"),
                        )
                        .order_by("pk")
                        .values("pk")[:1]
                    )
                )
                .values_list("pk", flat=True)
            )
            .prefetch_related("from_building__installs")
            .prefetch_related("from_building__nodes")
            .prefetch_related("to_building__installs")
            .prefetch_related("to_building__nodes")
        )

        los_based_potential_links = []
        for los in los_objects_with_installs:
            from_numbers = set(i.install_number for i in los.from_building.installs.all()).union(
                set(n.network_number for n in los.from_building.nodes.all() if n.network_number)
            )

            to_numbers = set(i.install_number for i in los.to_building.installs.all()).union(
                set(n.network_number for n in los.to_building.nodes.all() if n.network_number)
            )

            for from_number in from_numbers:
                for to_number in to_numbers:
                    los_based_potential_links.append(
                        {
                            "from": from_number,
                            "to": to_number,
                            "status": Link.LinkStatus.PLANNED.lower(),
                        }
                    )

        response.data.extend(los_based_potential_links)

        # Since all of the above logic is focused on node <-> node links (and install <-> node links)
        # it excludes device <-> AP and node <-> AP links for campus access points. We add these back
        # manually here
        ap_links_queryset = (
            Link.objects.filter(Q(from_device__accesspoint__isnull=False) | Q(to_device__accesspoint__isnull=False))
            .prefetch_related("to_device")
            .prefetch_related("from_device")
            .prefetch_related("to_device__node")
            .prefetch_related("from_device__node")
            .annotate(
                from_ap_id=Subquery(
                    AccessPoint.objects.filter(device_ptr=OuterRef("from_device")).values("device_ptr_id")[:1]
                )
            )
            .annotate(
                to_ap_id=Subquery(
                    AccessPoint.objects.filter(device_ptr=OuterRef("to_device")).values("device_ptr_id")[:1]
                )
            )
            .order_by("id")
        )
        ap_links = []
        for link in ap_links_queryset:
            ap_links.append(
                {
                    "from": (
                        convert_access_point_id_to_fake_node_number(link.from_ap_id)
                        if link.from_ap_id
                        else link.from_device.node.network_number
                    ),
                    "to": (
                        convert_access_point_id_to_fake_node_number(link.to_ap_id)
                        if link.to_ap_id
                        else link.to_device.node.network_number
                    ),
                    "status": MapDataLinkSerializer().convert_status_to_spreadsheet_status(link),
                }
            )

        response.data.extend(ap_links)

        return response


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
    queryset = (
        Sector.objects.filter(~Q(status__in=[Device.DeviceStatus.INACTIVE]))
        .exclude(node__network_number__isnull=True)
        .prefetch_related("node")
        .prefetch_related("node__installs")
    )


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary="Proxy for the city of new york LinkNYC kisok location dataset. Output in a JSON "
        "format that is compatible with the website map. (Warning: This endpoint is a legacy "
        "format and may be deprecated/removed in the future)",
        responses={
            "201": OpenApiResponse(
                inline_serializer(
                    "KioskData",
                    fields={
                        "street_address": serializers.CharField(),
                        "type": serializers.CharField(),
                        "id": serializers.IntegerField(),
                        "coordinates": serializers.ListField(
                            child=serializers.FloatField(), max_length=2, min_length=2
                        ),
                        "status": serializers.CharField(required=False),
                    },
                    many=True,
                ),
                description="Successfully fetched a list of all linkNYC kiosks in the city",
            ),
            "502": OpenApiResponse(
                inline_serializer("CityErrorResponse", fields={"detail": serializers.CharField()}),
                description="Missing or invalid response received from NYC dataset",
            ),
        },
    )
)
class KioskListWrapper(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request: Request) -> Response:
        try:
            response = requests.get(LINKNYC_KIOSK_DATA_URL)
            response.raise_for_status()
            data = response.json()

            if not data:
                raise ValueError("Expected at least one kiosk to be returned from the City of New York dataset")

            kiosks = []
            for row in data:
                coordinates = [float(row["longitude"]), float(row["latitude"])]
                kiosk_status = LINKNYC_KIOSK_STATUS_TRANSLATION.get(row["link_installation_status"])
                kiosks.append(
                    {
                        "street_address": row["street_address"],
                        "type": row["planned_kiosk_type"],
                        "id": row["link_site_id"],
                        "coordinates": coordinates,
                        "status": kiosk_status,
                    }
                )
            return Response(
                kiosks,
                status=status.HTTP_200_OK,
            )
        except requests.exceptions.RequestException:
            logging.exception("Error fetching data from City of New York LinkNYC kiosk dataset")
            return Response(
                {"detail": "Error fetching data from City of New York"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except (KeyError, JSONDecodeError, ValueError):
            logging.exception("Error decoding data from City of New York LinkNYC kiosk dataset")
            return Response(
                {"detail": "Invalid response received from City of New York"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
