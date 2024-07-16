from typing import Dict, List, Optional, Tuple

from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.http import HttpRequest, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from fastkml import Data, ExtendedData, geometry, kml, styles
from fastkml.enums import AltitudeMode
from pygeoif import LineString, Point
from rest_framework import permissions, status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.views import APIView

from meshapi.models import Install, Link
from meshapi.models.devices.device import Device
from meshapi.models.node import Node

KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml"
KML_CONTENT_TYPE_WITH_CHARSET = f"{KML_CONTENT_TYPE}; charset=utf-8"
DEFAULT_ALTITUDE = 5  # Meters (absolute)

ACTIVE_COLOR = "#F00"
INACTIVE_COLOR = "#CCC"

CITY_FOLDER_MAP = {
    "New York": "Manhattan",
    "Brooklyn": "Brooklyn",
    "Queens": "Queens",
    "Bronx": "The Bronx",
    "Staten Island": "Staten Island",
    None: "Other",
}


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

        kml_document = kml.Document(ns, styles=[grey_dot, red_dot, red_line, grey_line])
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

        for link in (
            Link.objects.prefetch_related("from_device")
            .prefetch_related("to_device")
            .filter(~Q(status=Link.LinkStatus.INACTIVE))
            .annotate(highest_altitude=Greatest("from_device__altitude", "to_device__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            # Logic to decide if this link should show up as active or not
            mark_active: bool = (
                # Link must be active
                link.status == Link.LinkStatus.ACTIVE
                # And the devices
                and link.from_device.status == Device.DeviceStatus.ACTIVE
                and link.to_device.status == Device.DeviceStatus.ACTIVE
                # And the device's nodes
                and link.from_device.node.status == Node.NodeStatus.ACTIVE
                and link.to_device.node.status == Node.NodeStatus.ACTIVE
            )
            node_label: str = f"{str(link.from_device.node)}-{str(link.to_device.node)}"
            placemark = kml.Placemark(
                name=f"Links-{link.id}",
                style_url=styles.StyleUrl(url="#red_line" if mark_active else "#grey_line"),
                kml_geometry=geometry.LineString(
                    geometry=LineString(
                        [
                            (
                                link.from_device.longitude,
                                link.from_device.latitude,
                                link.from_device.altitude or DEFAULT_ALTITUDE,
                            ),
                            (
                                link.to_device.longitude,
                                link.to_device.latitude,
                                link.to_device.altitude or DEFAULT_ALTITUDE,
                            ),
                        ]
                    ),
                    altitude_mode=AltitudeMode.absolute,
                    extrude=True,
                ),
            )

            from_identifier = link.from_device.node.network_number
            to_identifier = link.to_device.node.network_number

            extended_data = {
                "name": f"Links-{link.id}-{node_label}",
                "stroke": ACTIVE_COLOR if mark_active else INACTIVE_COLOR,
                "fill": "#000000",
                "fill-opacity": "0",
                "from": str(from_identifier),
                "to": str(to_identifier),
                "status": link.status,
                "type": link.type,
            }

            placemark.extended_data = ExtendedData(
                elements=[Data(name=key, value=val) for key, val in extended_data.items()]
            )

            if mark_active:
                active_links_folder.append(placemark)
            else:
                inactive_links_folder.append(placemark)

        return HttpResponse(
            kml_root.to_string(),
            content_type=KML_CONTENT_TYPE_WITH_CHARSET,
            status=status.HTTP_200_OK,
        )
