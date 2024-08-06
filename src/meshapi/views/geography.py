import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from django.db.models import Exists, F, OuterRef, Q
from django.db.models.functions import Greatest
from django.http import HttpRequest, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from fastkml import Data, ExtendedData, geometry, kml, styles
from fastkml.enums import AltitudeMode
from pygeoif import LineString, Point
from rest_framework import permissions, serializers, status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from meshapi.exceptions import AddressError
from meshapi.models import LOS, Install, Link
from meshapi.validation import geocode_nyc_address

KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml"
KML_CONTENT_TYPE_WITH_CHARSET = f"{KML_CONTENT_TYPE}; charset=utf-8"
DEFAULT_ALTITUDE = 5  # Meters (absolute)

ACTIVE_COLOR = "#F00"
INACTIVE_COLOR = "#777"
POTENTIAL_COLOR = "#CCC"

CITY_FOLDER_MAP = {
    "New York": "Manhattan",
    "Brooklyn": "Brooklyn",
    "Queens": "Queens",
    "Bronx": "The Bronx",
    "Staten Island": "Staten Island",
    None: "Other",
}

LinkKMLDict = TypedDict(
    "LinkKMLDict",
    {
        "link_label": str,
        "mark_active": bool,
        "is_los": bool,
        "from_coord": Tuple[float, float, float],
        "to_coord": Tuple[float, float, float],
        "extended_data": Dict[str, Any],
    },
)


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    def select_parser(self, request: HttpRequest, parsers: List[BaseParser]) -> BaseParser:  # type: ignore[override]
        """
        Select the first parser in the `.parser_classes` list.
        """
        return parsers[0]

    def select_renderer(
        self,
        request: HttpRequest,
        renderers: List[BaseRenderer],  # type: ignore[override]
        format_suffix: Optional[str] = None,
    ) -> Tuple[BaseRenderer, str]:
        """
        Select the first renderer in the `.renderer_classes` list.
        """
        return renderers[0], renderers[0].media_type


def create_placemark(identifier: str, point: Point, active: bool, status: str, roof_access: bool) -> kml.Placemark:
    placemark = kml.Placemark(
        name=identifier,
        style_url=styles.StyleUrl(url="#red_dot" if active else "#grey_dot"),
        kml_geometry=geometry.Point(
            geometry=point,
            altitude_mode=AltitudeMode.absolute,
        ),
    )

    extended_data = {
        "name": identifier,
        "roofAccess": str(roof_access),
        "marker-color": ACTIVE_COLOR if active else INACTIVE_COLOR,
        "id": identifier,
        "status": status,
        # Leave disabled, notes can leak a lot of information & this endpoint is public
        # "notes": install.notes,
    }

    placemark.extended_data = ExtendedData(elements=[Data(name=key, value=val) for key, val in extended_data.items()])

    return placemark


class WholeMeshKML(APIView):
    permission_classes = [permissions.AllowAny]
    content_negotiation_class = IgnoreClientContentNegotiation

    @extend_schema(
        tags=["Geographic & KML Data"],
        auth=[],
        summary="Generate a KML file which contains all nodes and links on the mesh",
        responses={
            (200, KML_CONTENT_TYPE): OpenApiResponse(
                OpenApiTypes.BINARY,
                description="Succesfully generated KML file. Returns XML Data conforming to the KML specification",
            )
        },
    )
    def get(self, request: HttpRequest) -> HttpResponse:
        kml_root = kml.KML()
        ns = "{http://www.opengis.net/kml/2.2}"

        grey_dot = styles.Style(
            id="grey_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        red_dot = styles.Style(
            id="red_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/red-circle.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        red_line = styles.Style(
            id="red_line",
            styles=[
                styles.LineStyle(color="ff0000ff", width=2),
                styles.PolyStyle(color="00000000", fill=False, outline=True),
            ],
        )

        grey_line = styles.Style(
            id="grey_line",
            styles=[
                styles.LineStyle(color="ffcccccc", width=2),
                styles.PolyStyle(color="00000000", fill=False, outline=True),
            ],
        )

        dark_grey_line = styles.Style(
            id="dark_grey_line",
            styles=[
                styles.LineStyle(color="ff777777", width=2),
                styles.PolyStyle(color="00000000", fill=False, outline=True),
            ],
        )

        kml_document = kml.Document(ns, styles=[grey_dot, red_dot, red_line, grey_line, dark_grey_line])
        kml_root.append(kml_document)

        nodes_folder = kml.Folder(name="Nodes")
        kml_document.append(nodes_folder)

        active_nodes_folder = kml.Folder(name="Active")
        nodes_folder.append(active_nodes_folder)
        inactive_nodes_folder = kml.Folder(name="Inactive")
        nodes_folder.append(inactive_nodes_folder)

        links_folder = kml.Folder(name="Links")
        kml_document.append(links_folder)

        active_links_folder = kml.Folder(name="Active")
        links_folder.append(active_links_folder)
        inactive_links_folder = kml.Folder(name="Inactive")
        links_folder.append(inactive_links_folder)

        active_folder_map: Dict[Optional[str], kml.Folder] = {}
        inactive_folder_map: Dict[Optional[str], kml.Folder] = {}

        for city_name, folder_name in CITY_FOLDER_MAP.items():
            active_folder_map[city_name] = kml.Folder(name=folder_name)
            inactive_folder_map[city_name] = kml.Folder(name=folder_name)
            active_nodes_folder.append(active_folder_map[city_name])
            inactive_nodes_folder.append(inactive_folder_map[city_name])

        mapped_nns = set()
        for install in (
            Install.objects.prefetch_related("node")
            .prefetch_related("building")
            .filter(
                ~Q(status__in=[Install.InstallStatus.CLOSED, Install.InstallStatus.NN_REASSIGNED])
                & Q(building__longitude__isnull=False)
                & Q(building__latitude__isnull=False)
            )
            .order_by("install_number")
        ):
            if install.status == Install.InstallStatus.ACTIVE:
                folder_map = active_folder_map
            else:
                folder_map = inactive_folder_map

            folder = folder_map[install.building.city if install.building.city in folder_map.keys() else None]

            install_placemark = create_placemark(
                str(install.install_number),
                Point(
                    install.building.longitude,
                    install.building.latitude,
                    install.building.altitude or DEFAULT_ALTITUDE,
                ),
                install.status == Install.InstallStatus.ACTIVE,
                install.status,
                install.roof_access,
            )
            folder.append(install_placemark)

            # Add an extra placemark for the Node, once for each NN
            # this makes searching much easier
            if install.node and install.node.network_number not in mapped_nns:
                node_placemark = create_placemark(
                    str(install.node.network_number),
                    Point(
                        install.node.longitude,
                        install.node.latitude,
                        install.node.altitude or DEFAULT_ALTITUDE,
                    ),
                    False,
                    install.node.status,
                    roof_access=False,
                )
                folder.append(node_placemark)
                mapped_nns.add(install.node.network_number)

        all_links_set = set()
        kml_links: List[LinkKMLDict] = []
        for link in (
            Link.objects.prefetch_related("from_device")
            .prefetch_related("to_device")
            .filter(~Q(status=Link.LinkStatus.INACTIVE))
            .exclude(type=Link.LinkType.VPN)
            .annotate(highest_altitude=Greatest("from_device__altitude", "to_device__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            mark_active: bool = link.status == Link.LinkStatus.ACTIVE
            link_label: str = f"{str(link.from_device.node)}-{str(link.to_device.node)}"
            from_identifier = link.from_device.node.network_number
            to_identifier = link.to_device.node.network_number

            all_links_set.add(tuple(sorted((from_identifier, to_identifier))))
            kml_links.append(
                {
                    "link_label": link_label,
                    "mark_active": mark_active,
                    "is_los": False,
                    "from_coord": (
                        link.from_device.longitude,
                        link.from_device.latitude,
                        link.from_device.altitude or DEFAULT_ALTITUDE,
                    ),
                    "to_coord": (
                        link.to_device.longitude,
                        link.to_device.latitude,
                        link.to_device.altitude or DEFAULT_ALTITUDE,
                    ),
                    "extended_data": {
                        "name": f"Links-{link.id}-{link_label}",
                        "stroke": ACTIVE_COLOR if mark_active else INACTIVE_COLOR,
                        "fill": "#000000",
                        "fill-opacity": "0",
                        "from": str(from_identifier),
                        "to": str(to_identifier),
                        "status": link.status,
                        "type": link.type,
                    },
                }
            )

        for los in (
            LOS.objects.filter(
                Exists(Install.objects.filter(building=OuterRef("from_building")))
                & Exists(Install.objects.filter(building=OuterRef("to_building")))
                & ~Q(from_building=F("to_building"))
            )
            .exclude(
                # Remove any LOS objects that would duplicate Link objects,
                # to avoid cluttering the file
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
            .prefetch_related("from_building")
            .prefetch_related("from_building__installs")
            .prefetch_related("to_building")
            .prefetch_related("to_building__installs")
            .annotate(highest_altitude=Greatest("from_building__altitude", "to_building__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            representative_from_install = min(los.from_building.installs.all().values_list("install_number", flat=True))
            representative_to_install = min(los.to_building.installs.all().values_list("install_number", flat=True))
            link_label = f"{representative_from_install}-{representative_to_install}"

            link_tuple = tuple(sorted((representative_from_install, representative_to_install)))
            if link_tuple not in all_links_set:
                all_links_set.add(link_tuple)
                kml_links.append(
                    {
                        "link_label": link_label,
                        "mark_active": False,
                        "is_los": True,
                        "from_coord": (
                            los.from_building.longitude,
                            los.from_building.latitude,
                            los.from_building.altitude or DEFAULT_ALTITUDE,
                        ),
                        "to_coord": (
                            los.to_building.longitude,
                            los.to_building.latitude,
                            los.to_building.altitude or DEFAULT_ALTITUDE,
                        ),
                        "extended_data": {
                            "name": f"LOS-{los.id} {link_label}",
                            "stroke": POTENTIAL_COLOR,
                            "fill": "#000000",
                            "fill-opacity": "0",
                            "from": f"#{representative_from_install} ({los.from_building.street_address})",
                            "to": f"#{representative_to_install} ({los.to_building.street_address})",
                            "source": los.source,
                        },
                    }
                )

        for link_dict in kml_links:
            placemark = kml.Placemark(
                name=f"Links-{link_dict['link_label']}",
                style_url=styles.StyleUrl(
                    url="#grey_line"
                    if link_dict["is_los"]
                    else ("#red_line" if link_dict["mark_active"] else "#dark_grey_line")
                ),
                kml_geometry=geometry.LineString(
                    geometry=LineString([link_dict["from_coord"], link_dict["to_coord"]]),
                    altitude_mode=AltitudeMode.absolute,
                    extrude=True,
                ),
            )

            placemark.extended_data = ExtendedData(
                elements=[Data(name=key, value=val) for key, val in link_dict["extended_data"].items()]
            )

            if link_dict["mark_active"]:
                active_links_folder.append(placemark)
            else:
                inactive_links_folder.append(placemark)

        return HttpResponse(
            kml_root.to_string(),
            content_type=KML_CONTENT_TYPE_WITH_CHARSET,
            status=status.HTTP_200_OK,
        )


@dataclass
class GeocodeRequest:
    street_address: str
    city: str
    state: str
    zip: int


class GeocodeSerializer(DataclassSerializer):
    class Meta:
        dataclass = GeocodeRequest


@extend_schema_view(
    get=extend_schema(
        tags=["Geographic & KML Data"],
        summary="Use the NYC geocoding APIs to look up an address, and return the lat/lon/alt "
        "corresponding to it or 404 if the address cannot be found within NYC",
        parameters=[GeocodeSerializer],
        responses={
            "201": OpenApiResponse(
                inline_serializer(
                    "JoinFormSuccessResponse",
                    fields={
                        "BIN": serializers.IntegerField(),
                        "latitude": serializers.FloatField(),
                        "longitude": serializers.FloatField(),
                        "altitude": serializers.FloatField(required=False),
                    },
                ),
                description="Request received, an install has been created (along with member and "
                "building objects if necessary).",
            ),
            "400": OpenApiResponse(
                inline_serializer("ErrorResponseMissingFields", fields={"detail": serializers.DictField()}),
                description="Invalid request body JSON or missing required fields",
            ),
            "404": OpenApiResponse(
                inline_serializer("ErrorResponseInvalidAddr", fields={"detail": serializers.CharField()}),
                description="Invalid address, or not found within NYC",
            ),
            "500": OpenApiResponse(
                inline_serializer("ErrorResponseInternalFailure", fields={"detail": serializers.CharField()}),
                description="Could not geocode address due to internal failure. Try again?",
            ),
        },
    )
)
class NYCGeocodeWrapper(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = GeocodeSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_addr: GeocodeRequest = serializer.save()
            nyc_addr_info = geocode_nyc_address(raw_addr.street_address, raw_addr.city, raw_addr.state, raw_addr.zip)
        except ValueError:
            return Response(
                {
                    "detail": "Non-NYC registrations are not supported at this time. "
                    "Please email support@nycmesh.net for more information"
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except AddressError as e:
            logging.exception("AddressError when validating address")
            return Response({"detail": e.args[0]}, status=status.HTTP_404_NOT_FOUND)

        if not nyc_addr_info:
            # We failed to contact the city, this is probably a retryable error, return 500
            return Response(
                {"detail": "Your address could not be validated."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "BIN": nyc_addr_info.bin,
                "latitude": nyc_addr_info.latitude,
                "longitude": nyc_addr_info.longitude,
                "altitude": nyc_addr_info.altitude,
            },
            status=status.HTTP_200_OK,
        )
