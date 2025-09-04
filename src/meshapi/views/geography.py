import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

from django.db.models import Exists, F, OuterRef, Q
from django.db.models.functions import Greatest
from django.http import HttpRequest, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from fastkml import Data, ExtendedData, geometry, kml, styles
from fastkml.enums import AltitudeMode
from pygeoif import LineString, Point
from rest_framework import permissions, serializers, status as http_status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from meshapi.exceptions import InvalidAddressError, UnsupportedAddressError
from meshapi.models import LOS, Install, Link
from meshapi.validation import geocode_nyc_address
from meshapi.views.forms import INVALID_ADDRESS_RESPONSE, UNSUPPORTED_ADDRESS_RESPONSE, VALIDATION_500_RESPONSE

KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml"
KML_CONTENT_TYPE_WITH_CHARSET = f"{KML_CONTENT_TYPE}; charset=utf-8"
DEFAULT_ALTITUDE = 5  # Meters (absolute)

ACTIVE_COLOR = "#F82C55"
INACTIVE_COLOR = "#979797"
POTENTIAL_COLOR = "#A87B84"
HUB_COLOR = "#5AC8FA"

# Node type colors - updated to match the icon colors
STANDARD_COLOR = "#F82C55"  # Red - Same as ACTIVE_COLOR
SUPERNODE_COLOR = "#0000FF" # Blue - same as Hub
POP_COLOR = "#FFCC00"       # Yellow - to match yellow_dot
AP_COLOR = "#00FF00"        # Green - to match green_dot
REMOTE_COLOR = "#800080"    # Purple - to match purple_dot
HUB_COLOR = "#0000FF"       # Blue - closest to teal available

# Create a mapping of node types to colors
NODE_TYPE_COLORS = {
    "Standard": STANDARD_COLOR,
    "Hub": HUB_COLOR,
    "Supernode": SUPERNODE_COLOR,
    "POP": POP_COLOR,
    "AP": AP_COLOR,
    "Remote": REMOTE_COLOR,
}

def hex_to_kml_color(hex_color, alpha=255):
    """Convert hex color (#RRGGBB) to KML color format (AABBGGRR)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"{alpha:02x}{b}{g}{r}"

# Define link type colors
LINK_TYPE_COLORS = {
    "5 GHz": "#297AFE",      
    "6 GHz": "#29BEFE",      
    "24 GHz": "#33BDBA",     
    "60 GHz": "#44FCF9",     
    "70-80 GHz": "#AAFFFE",  
    "VPN": "#7F0093",        
    "Fiber": "#F6BE00",      
    "Ethernet": "#A07B00",   
    "Other": "#2D2D2D",      
}

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


def create_placemark(identifier: str, point: Point, active: bool, status: str, roof_access: bool, node_type: str = None) -> kml.Placemark:
    # Determine the appropriate style based on node type and active status
    if node_type in ["Hub", "Supernode", "POP", "AP", "Remote"]:
        # Map node types to style URLs based on user's color preferences
        style_map = {
            "Hub": "#blue_dot",          # Hub should be blue
            "Supernode": "#blue_dot",    # Supernode should also be blue
            "POP": "#yellow_dot",        # POP should be yellow
            "AP": "#green_dot",          # AP should be green
            "Remote": "#purple_dot",     # Remote should be purple
        }
        style_url_value = style_map.get(node_type, "#red_dot")
    elif active:
        style_url_value = "#red_dot"  # Standard active
    else:
        style_url_value = "#grey_dot"  # Inactive
    
    placemark = kml.Placemark(
        name=identifier,
        style_url=styles.StyleUrl(url=style_url_value),
        kml_geometry=geometry.Point(
            geometry=point,
            altitude_mode=AltitudeMode.absolute,
        ),
    )

    # Determine the marker color based on node type and active status
    if node_type and node_type in NODE_TYPE_COLORS:
        marker_color = NODE_TYPE_COLORS[node_type]
    elif active:
        marker_color = ACTIVE_COLOR
    else:
        marker_color = INACTIVE_COLOR

    extended_data = {
        "name": identifier,
        "roofAccess": str(roof_access),
        "marker-color": marker_color,
        "id": identifier,
        "status": status,
        "nodeType": node_type or "Standard",  # Add node type to extended data
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

        blue_dot = styles.Style(
            id="blue_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/blu-circle.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        # Style definitions for node types based on user's color preferences
        orange_dot = styles.Style(
            id="orange_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/orange-circle.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        green_dot = styles.Style(
            id="green_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/grn-circle.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        yellow_dot = styles.Style(
            id="yellow_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png"),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        purple_dot = styles.Style(
            id="purple_dot",
            styles=[
                styles.IconStyle(
                    icon=styles.Icon(href="http://maps.google.com/mapfiles/kml/paddle/purple-circle.png"),
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

        # Create style definitions for each link type
        link_styles = []
        for link_type, color in LINK_TYPE_COLORS.items():
            # Active style
            link_styles.append(
                styles.Style(
                    id=f"{link_type.replace(' ', '_').replace('-', '_')}_active_line",
                    styles=[
                        styles.LineStyle(color=hex_to_kml_color(color), width=2),
                        styles.PolyStyle(color="00000000", fill=False, outline=True),
                    ],
                )
            )
            
            # Inactive style (using a semi-transparent version of the color)
            link_styles.append(
                styles.Style(
                    id=f"{link_type.replace(' ', '_').replace('-', '_')}_inactive_line",
                    styles=[
                        styles.LineStyle(color=hex_to_kml_color(color, alpha=128), width=2),
                        styles.PolyStyle(color="00000000", fill=False, outline=True),
                    ],
                )
            )

        kml_document = kml.Document(
            ns,
            styles=[
                grey_dot, red_dot, blue_dot,
                orange_dot, green_dot, yellow_dot, purple_dot,
                red_line, grey_line, dark_grey_line
            ] + link_styles
        )
        kml_root.append(kml_document)

        nodes_folder = kml.Folder(name="Nodes")
        kml_document.append(nodes_folder)

        active_nodes_folder = kml.Folder(name="Active")
        nodes_folder.append(active_nodes_folder)
        inactive_nodes_folder = kml.Folder(name="Inactive")
        nodes_folder.append(inactive_nodes_folder)

        # Create node type folders under active/inactive
        active_node_type_folders = {}
        inactive_node_type_folders = {}
        
        # Define all node types
        node_types = ["Standard", "Hub", "Supernode", "POP", "AP", "Remote"]
        
        # Create folders for each node type
        for node_type in node_types:
            folder_name = f"{node_type} Nodes"
            
            # Create active folder for this node type
            active_node_type_folders[node_type] = kml.Folder(name=folder_name)
            active_nodes_folder.append(active_node_type_folders[node_type])
            
            # Create inactive folder for this node type
            inactive_node_type_folders[node_type] = kml.Folder(name=folder_name)
            inactive_nodes_folder.append(inactive_node_type_folders[node_type])

        links_folder = kml.Folder(name="Links")
        kml_document.append(links_folder)

        active_links_folder = kml.Folder(name="Active")
        links_folder.append(active_links_folder)
        inactive_links_folder = kml.Folder(name="Inactive")
        links_folder.append(inactive_links_folder)

        # Create type folders under active and inactive
        active_type_folders = {}
        inactive_type_folders = {}
        for link_type in list(LINK_TYPE_COLORS.keys()):
            active_type_folders[link_type] = kml.Folder(name=link_type)
            active_links_folder.append(active_type_folders[link_type])
            inactive_type_folders[link_type] = kml.Folder(name=link_type)
            inactive_links_folder.append(inactive_type_folders[link_type])

        # These maps are no longer used with the new folder structure
        # but kept as empty dicts to avoid changing too much code
        active_hub_folder_map: Dict[Optional[str], kml.Folder] = {}
        active_standard_folder_map: Dict[Optional[str], kml.Folder] = {}
        inactive_hub_folder_map: Dict[Optional[str], kml.Folder] = {}
        inactive_standard_folder_map: Dict[Optional[str], kml.Folder] = {}

        # for city_name, folder_name in CITY_FOLDER_MAP.items():
        #     # Create city folders under hub nodes
        #     active_hub_folder_map[city_name] = kml.Folder(name=folder_name)
        #     inactive_hub_folder_map[city_name] = kml.Folder(name=folder_name)
        #     active_hub_folder.append(active_hub_folder_map[city_name])
        #     inactive_hub_folder.append(inactive_hub_folder_map[city_name])

        #     # Create city folders under standard nodes
        #     active_standard_folder_map[city_name] = kml.Folder(name=folder_name)
        #     inactive_standard_folder_map[city_name] = kml.Folder(name=folder_name)
        #     active_standard_folder.append(active_standard_folder_map[city_name])
        #     inactive_standard_folder.append(inactive_standard_folder_map[city_name])
        ## No city-based subfolders - nodes go directly into hub/standard folders

        # Create a dictionary to map coordinates to installs and nodes
        location_map = {}  # Key: (lon, lat), Value: {'installs': [], 'node': None, 'active': False}
        
        # First pass: group installs by location
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
            # Create a location key based on coordinates
            location_key = (install.building.longitude, install.building.latitude)
            
            # Initialize location entry if it doesn't exist
            if location_key not in location_map:
                location_map[location_key] = {
                    'installs': [],
                    'node': None,
                    'active': False,
                    'altitude': install.building.altitude or DEFAULT_ALTITUDE,
                    'roof_access': False
                }
            
            # Add this install to the location
            location_map[location_key]['installs'].append(install)
            
            # Track if any install at this location is active
            if install.status == Install.InstallStatus.ACTIVE:
                location_map[location_key]['active'] = True
            
            # Track if any install has roof access
            if install.roof_access:
                location_map[location_key]['roof_access'] = True
            
            # If this install has a node with a network number, store it
            if install.node and install.node.network_number:
                location_map[location_key]['node'] = install.node
        
        # Second pass: create one placemark per unique location
        for location, data in location_map.items():
            lon, lat = location
            installs = data['installs']
            node = data['node']
            is_active = data['active']
            altitude = data['altitude']
            roof_access = data['roof_access']
            
            # Determine the primary identifier and properties for the placemark
            if node:
                # Prioritize node network number as identifier
                identifier = str(node.network_number)
                node_type = node.type or "Standard"
                status = node.status
            else:
                # Use the first install as the primary if no node exists
                identifier = str(installs[0].install_number)
                node_type = installs[0].node.type if installs[0].node else "Standard"
                status = installs[0].status
            
            # Get all install numbers at this location
            install_numbers = [str(install.install_number) for install in installs]
            
            # Determine which folder to use based on node type and active status
            if is_active:
                folder = active_node_type_folders.get(node_type, active_node_type_folders["Standard"])
            else:
                folder = inactive_node_type_folders.get(node_type, inactive_node_type_folders["Standard"])
            
            # Create the placemark
            placemark = create_placemark(
                identifier,
                Point(lon, lat, altitude),
                is_active,
                status,
                roof_access,
                node_type,
            )
            
            # Add install numbers to the extended data
            placemark.extended_data.elements.append(Data(name="installNumbers", value=",".join(install_numbers)))
            
            # Add to the appropriate folder
            folder.append(placemark)

        all_links_set = set()
        kml_links: List[LinkKMLDict] = []
        for link in (
            Link.objects.prefetch_related("from_device")
            .prefetch_related("to_device")
            .filter(~Q(status=Link.LinkStatus.INACTIVE))
            .filter(from_device__node__network_number__isnull=False)
            .filter(to_device__node__network_number__isnull=False)
            .exclude(type=Link.LinkType.VPN)
            .annotate(highest_altitude=Greatest("from_device__node__altitude", "to_device__node__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            mark_active: bool = link.status == Link.LinkStatus.ACTIVE
            link_label: str = f"{str(link.from_device.node)}-{str(link.to_device.node)}"
            from_identifier = cast(  # Cast is safe due to corresponding filter above
                int, link.from_device.node.network_number
            )
            to_identifier = cast(  # Cast is safe due to corresponding filter above
                int, link.to_device.node.network_number
            )

            all_links_set.add(tuple(sorted((from_identifier, to_identifier))))
            kml_links.append(
                {
                    "link_label": link_label,
                    "mark_active": mark_active,
                    "is_los": False,
                    "from_coord": (
                        link.from_device.node.longitude,
                        link.from_device.node.latitude,
                        link.from_device.node.altitude or DEFAULT_ALTITUDE,
                    ),
                    "to_coord": (
                        link.to_device.node.longitude,
                        link.to_device.node.latitude,
                        link.to_device.node.altitude or DEFAULT_ALTITUDE,
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
            # Determine link type
            link_type = link_dict["extended_data"].get("type")
            if not link_type or link_type not in LINK_TYPE_COLORS:
                link_type = "Other"
            
            # Create style URL based on type and active status
            style_id = f"{link_type.replace(' ', '_').replace('-', '_')}_{'active' if link_dict['mark_active'] else 'inactive'}_line"
            
            placemark = kml.Placemark(
                name=f"Links-{link_dict['link_label']}",
                style_url=styles.StyleUrl(
                    url=(
                        "#grey_line"
                        if link_dict["is_los"]
                        else f"#{style_id}"
                    )
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

            # Add to the appropriate folder based on type and active status
            if link_dict["is_los"]:
                # LOS links still go to active/inactive folders directly
                if link_dict["mark_active"]:
                    active_links_folder.append(placemark)
                else:
                    inactive_links_folder.append(placemark)
            else:
                if link_dict["mark_active"]:
                    active_type_folders[link_type].append(placemark)
                else:
                    inactive_type_folders[link_type].append(placemark)

        return HttpResponse(
            kml_root.to_string(),
            content_type=KML_CONTENT_TYPE_WITH_CHARSET,
            status=http_status.HTTP_200_OK,
        )


@dataclass
class GeocodeRequest:
    street_address: str
    city: str
    state: str
    zip: str


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
                    "GeocodeSuccessResponse",
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
            return Response({"detail": serializer.errors}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            raw_addr: GeocodeRequest = serializer.save()
            nyc_addr_info = geocode_nyc_address(raw_addr.street_address, raw_addr.city, raw_addr.state, raw_addr.zip)
        except UnsupportedAddressError:
            return Response(
                {"detail": UNSUPPORTED_ADDRESS_RESPONSE},
                status=http_status.HTTP_404_NOT_FOUND,
            )
        except InvalidAddressError:
            logging.exception("InvalidAddressError when validating address")
            return Response({"detail": INVALID_ADDRESS_RESPONSE}, status=http_status.HTTP_404_NOT_FOUND)

        except Exception:
            # We failed to contact the city, this is probably a retryable error, return 500
            return Response({"detail": VALIDATION_500_RESPONSE}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "BIN": nyc_addr_info.bin,
                "latitude": nyc_addr_info.latitude,
                "longitude": nyc_addr_info.longitude,
                "altitude": nyc_addr_info.altitude,
            },
            status=http_status.HTTP_200_OK,
        )
