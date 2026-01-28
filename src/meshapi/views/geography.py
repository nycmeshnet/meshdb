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
from meshapi.models import LOS, Install, Link, Node
from meshapi.validation import geocode_nyc_address
from meshapi.views.forms import INVALID_ADDRESS_RESPONSE, UNSUPPORTED_ADDRESS_RESPONSE, VALIDATION_500_RESPONSE

KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml"
KML_CONTENT_TYPE_WITH_CHARSET = f"{KML_CONTENT_TYPE}; charset=utf-8"
DEFAULT_ALTITUDE = 5  # Meters (absolute)

# Define node type colors
ACTIVE_COLOR = "#F82C55"
HUB_COLOR = "#5AC8FA"
STANDARD_COLOR = "#F82C55"
SUPERNODE_COLOR = "#297AFE"
POP_COLOR = "#F6BE00"
AP_COLOR = "#38E708"
REMOTE_COLOR = "#800080"
HUB_COLOR = "#5AC8FA"

# Define link type colors
LOS_COLOR = "#000000"
LINK_TYPE_COLORS = {
    "Other": "#2D2D2D",
    "VPN": "#7F0093",
    "5 GHz": "#297AFE",      
    "6 GHz": "#41A3FF",      
    "24 GHz": "#40D1EE",     
    "60 GHz": "#44FCF9",     
    "70-80 GHz": "#44FCDD",  
    "Fiber": "#F6BE00",      
    "Ethernet": "#A07B00",
}

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

DOT_SIZE = 1
DOT_URL = "http://maps.google.com/mapfiles/kml/shapes/dot.png"

LinkKMLDict = TypedDict(
    "LinkKMLDict",
    {
        "link_label": str,
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


def create_placemark(identifier: str, point: Point, status: str, node_type: str = None, node_name: str = None) -> kml.Placemark:
    # Determine the appropriate style based on node type
    if node_type in ["Hub", "Supernode", "POP", "AP", "Remote"]:
        # Map node types to style URLs based on user's color preferences
        style_map = {
            "Hub": "#hub_dot",           # Hub should be teal blue
            "Supernode": "#blue_dot",    # Supernode should be blue
            "POP": "#yellow_dot",        # POP should be yellow
            "AP": "#green_dot",          # AP should be green
            "Remote": "#purple_dot",     # Remote should be purple
        }
        style_url_value = style_map.get(node_type, "#red_dot")
    else:
        style_url_value = "#red_dot"  # Standard node
    
    placemark = kml.Placemark(
        name=identifier,
        style_url=styles.StyleUrl(url=style_url_value),
        kml_geometry=geometry.Point(
            geometry=point,
            altitude_mode=AltitudeMode.absolute,
        ),
    )

    extended_data = {
        "name": node_name if node_name else f"NN {identifier}",
        "nodeType": node_type or "Standard",  # Add node type to extended data
        "status": status,
        "id": identifier,
    }

    placemark.extended_data = ExtendedData(elements=[Data(name=key, value=val) for key, val in extended_data.items()])

    return placemark


class WholeMeshKML(APIView):
    permission_classes = [permissions.AllowAny]
    content_negotiation_class = IgnoreClientContentNegotiation
    
    def prioritize_links(self, kml_links):
        # Define priority order (lower number = higher priority)
        priority_order = {
            "Fiber": 1,
            "Ethernet": 2,
            "70-80 GHz": 3,
            "60 GHz": 4,
            "24 GHz": 5,
            "6 GHz": 6,
            "5 GHz": 7,
            "Other": 8,
            "VPN": 9
        }
        
        # Group links by coordinates
        link_groups = {}
        for link in kml_links:
            # Create canonical representation of coordinates
            # Sort coordinates to ensure consistent ordering regardless of from/to direction
            coords = [link["from_coord"], link["to_coord"]]
            coords.sort()  # Sort to ensure consistent ordering
            key = tuple(map(tuple, coords))  # Convert to hashable type
            
            if key not in link_groups:
                link_groups[key] = []
            link_groups[key].append(link)
        
        # Select highest priority link from each group
        prioritized_links = []
        for group in link_groups.values():
            if len(group) == 1:
                # Only one link in this group, no need to prioritize
                prioritized_links.append(group[0])
            else:
                # Multiple links, select the one with highest priority
                best_link = group[0]
                best_priority = priority_order.get(best_link["extended_data"].get("type", "Other"), 9)
                
                for link in group[1:]:
                    link_type = link["extended_data"].get("type", "Other")
                    link_priority = priority_order.get(link_type, 9)
                    
                    if link_priority < best_priority:
                        best_link = link
                        best_priority = link_priority
                
                prioritized_links.append(best_link)
        
        return prioritized_links

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

        # Use a simple dot.png for all styles and apply custom colors

        red_dot = styles.Style(
            id="red_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(STANDARD_COLOR),
                    scale=DOT_SIZE,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        blue_dot = styles.Style(
            id="blue_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(SUPERNODE_COLOR),
                    scale=DOT_SIZE + 1,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        # Add a specific style for Hub nodes
        hub_dot = styles.Style(
            id="hub_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(HUB_COLOR),
                    scale=DOT_SIZE + 0.5,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        # Style definitions for node types based on user's color preferences
        green_dot = styles.Style(
            id="green_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(AP_COLOR),
                    scale=DOT_SIZE,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        yellow_dot = styles.Style(
            id="yellow_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(POP_COLOR),
                    scale=DOT_SIZE + 1,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        purple_dot = styles.Style(
            id="purple_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(REMOTE_COLOR),
                    scale=DOT_SIZE,
                    icon=styles.Icon(href=DOT_URL),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        los_line = styles.Style(
            id="los_line",
            styles=[
                styles.LineStyle(color=hex_to_kml_color(LOS_COLOR), width=2),
                styles.PolyStyle(color="00000000", fill=False, outline=True),
            ],
        )

        # Create style definitions for each link type
        link_styles = []
        for link_type, color in LINK_TYPE_COLORS.items():
            link_styles.append(
                styles.Style(
                    id=f"{link_type.replace(' ', '_').replace('-', '_')}_line",
                    styles=[
                        styles.LineStyle(color=hex_to_kml_color(color), width=2),
                        styles.PolyStyle(color="00000000", fill=False, outline=True),
                    ],
                )
            )

        kml_document = kml.Document(
            ns,
            styles=[
                red_dot, blue_dot, hub_dot,
                green_dot, yellow_dot, purple_dot,
                los_line
            ] + link_styles
        )
        kml_root.append(kml_document)

        nodes_folder = kml.Folder(name="Nodes")
        kml_document.append(nodes_folder)

        # Create node type folders
        node_type_folders = {}
        
        # Define all node types
        node_types = ["Standard", "Hub", "Supernode", "POP", "AP", "Remote"]
        
        # Create folders for each node type
        for node_type in node_types:
            folder_name = f"{node_type} Nodes"
            
            # Create folder for this node type
            node_type_folders[node_type] = kml.Folder(name=folder_name)
            nodes_folder.append(node_type_folders[node_type])

        links_folder = kml.Folder(name="Links")
        kml_document.append(links_folder)

        # Create type folders for links
        type_folders = {}
        for link_type in list(LINK_TYPE_COLORS.keys()):
            type_folders[link_type] = kml.Folder(name=link_type)
            links_folder.append(type_folders[link_type])
            
        # Create a dedicated folder for LOS links
        los_folder = kml.Folder(name="LOS")
        links_folder.append(los_folder)

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
            # Prioritize node coordinates if available
            if install.node and install.node.latitude is not None and install.node.longitude is not None:
                location_key = (install.node.longitude, install.node.latitude)
                altitude = install.node.altitude or DEFAULT_ALTITUDE
            else:
                location_key = (install.building.longitude, install.building.latitude)
                altitude = install.building.altitude or DEFAULT_ALTITUDE
            
            # Initialize location entry if it doesn't exist
            if location_key not in location_map:
                location_map[location_key] = {
                    'installs': [],
                    'node': None,
                    'active': False,
                    'altitude': altitude,
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
        
        # Additional pass: add active nodes that might not have active installs
        for node in (
            Node.objects.filter(status=Node.NodeStatus.ACTIVE)
            .filter(latitude__isnull=False)
            .filter(longitude__isnull=False)
        ):
            # Create a location key based on coordinates
            location_key = (node.longitude, node.latitude)
            
            # Initialize location entry if it doesn't exist
            if location_key not in location_map:
                location_map[location_key] = {
                    'installs': [],
                    'node': node,
                    'active': True,  # Mark as active since the node is active
                    'altitude': node.altitude or DEFAULT_ALTITUDE,
                    'roof_access': False
                }
            else:
                # Update existing location with node information if not already set
                if not location_map[location_key]['node']:
                    location_map[location_key]['node'] = node
                # Mark as active since the node is active
                location_map[location_key]['active'] = True
        
        # Second pass: create one placemark per unique location
        for location, data in location_map.items():
            lon, lat = location
            installs = data['installs']
            node = data['node']
            is_active = data['active']
            altitude = data['altitude']
            
            # Skip inactive nodes
            if not is_active:
                continue
            
            # Determine the primary identifier and properties for the placemark
            if node:
                # Prioritize network number (NN) as identifier
                identifier = str(node.network_number)
                node_type = node.type or "Standard"
                status = node.status
                node_name = node.name  # Get the colloquial name if available
            else:
                # Use the first install as the primary if no node exists
                identifier = str(installs[0].install_number)
                node_type = installs[0].node.type if installs[0].node else "Standard"
                status = installs[0].status
                node_name = installs[0].node.name if installs[0].node else None  # Get the node name if available
            
            # Get only active install numbers at this location
            active_installs = [install for install in installs if install.status == Install.InstallStatus.ACTIVE]
            install_numbers = [str(install.install_number) for install in active_installs]
            
            # Determine which folder to use based on node type
            folder = node_type_folders.get(node_type, node_type_folders["Standard"])
            
            # Create the placemark
            placemark = create_placemark(
                identifier,
                Point(lon, lat, altitude),
                status,
                node_type,
                node_name,
            )
            
            # Add install numbers to the extended data
            placemark.extended_data.elements.append(Data(name="install_numbers", value=",".join(install_numbers)))
            
            # Add the total count of active installs
            placemark.extended_data.elements.append(Data(name="install_count", value=str(len(install_numbers))))
            
            # Add install_date if available (from the earliest active install)
            if active_installs:
                # Get the earliest install_date from active installs
                install_dates = [install.install_date for install in active_installs if install.install_date]
                if install_dates:
                    earliest_install_date = min(install_dates)
                    placemark.extended_data.elements.append(Data(name="install_date", value=earliest_install_date.isoformat()))
            
            # Add to the appropriate folder
            folder.append(placemark)

        all_links_set = set()
        kml_links: List[LinkKMLDict] = []
        for link in (
            Link.objects.prefetch_related("from_device")
            .prefetch_related("to_device")
            .filter(status=Link.LinkStatus.ACTIVE)  # Only include active links
            .filter(from_device__node__network_number__isnull=False)
            .filter(to_device__node__network_number__isnull=False)
            .exclude(type=Link.LinkType.VPN)
            .annotate(highest_altitude=Greatest("from_device__node__altitude", "to_device__node__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            link_label: str = f"{str(link.from_device.node)}<->{str(link.to_device.node)}"
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
                        "type": link.type,
                        "status": link.status,
                        "from": str(from_identifier),
                        "to": str(to_identifier),
                        "install_date": link.install_date.isoformat() if link.install_date else None,
                    },
                }
            )

        for los in (
            LOS.objects.filter(
                Exists(Install.objects.filter(building=OuterRef("from_building"), status=Install.InstallStatus.ACTIVE))
                & Exists(Install.objects.filter(building=OuterRef("to_building"), status=Install.InstallStatus.ACTIVE))
                & ~Q(from_building=F("to_building"))
            )
            .exclude(
                # Remove any LOS objects that would duplicate Link objects
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
            .prefetch_related("from_building__primary_node")  # Prefetch primary_node
            .prefetch_related("to_building")
            .prefetch_related("to_building__installs")
            .prefetch_related("to_building__primary_node")  # Prefetch primary_node
            .annotate(highest_altitude=Greatest("from_building__altitude", "to_building__altitude"))
            .order_by(F("highest_altitude").asc(nulls_first=True))
        ):
            representative_from_install = min(los.from_building.installs.all().values_list("install_number", flat=True))
            representative_to_install = min(los.to_building.installs.all().values_list("install_number", flat=True))
            link_label = f"{representative_from_install}<->{representative_to_install}"

            link_tuple = tuple(sorted((representative_from_install, representative_to_install)))
            if link_tuple not in all_links_set:
                all_links_set.add(link_tuple)
                
                # Get from coordinates - prioritize node coordinates if available
                if los.from_building.primary_node and los.from_building.primary_node.latitude is not None and los.from_building.primary_node.longitude is not None:
                    from_coord = (
                        los.from_building.primary_node.longitude,
                        los.from_building.primary_node.latitude,
                        los.from_building.primary_node.altitude or DEFAULT_ALTITUDE,
                    )
                else:
                    from_coord = (
                        los.from_building.longitude,
                        los.from_building.latitude,
                        los.from_building.altitude or DEFAULT_ALTITUDE,
                    )
                
                # Get to coordinates - prioritize node coordinates if available
                if los.to_building.primary_node and los.to_building.primary_node.latitude is not None and los.to_building.primary_node.longitude is not None:
                    to_coord = (
                        los.to_building.primary_node.longitude,
                        los.to_building.primary_node.latitude,
                        los.to_building.primary_node.altitude or DEFAULT_ALTITUDE,
                    )
                else:
                    to_coord = (
                        los.to_building.longitude,
                        los.to_building.latitude,
                        los.to_building.altitude or DEFAULT_ALTITUDE,
                    )
                
                kml_links.append(
                    {
                        "link_label": link_label,
                        "is_los": True,
                        "from_coord": from_coord,
                        "to_coord": to_coord,
                        "extended_data": {
                            "from": f"#{representative_from_install} ({los.from_building.street_address})",
                            "to": f"#{representative_to_install} ({los.to_building.street_address})",
                            "source": los.source,
                        },
                    }
                )

        # Prioritize links to show higher frequency links when there are duplicates
        kml_links = self.prioritize_links(kml_links)
        
        for link_dict in kml_links:
            # Determine link type
            link_type = link_dict["extended_data"].get("type")
            if not link_type or link_type not in LINK_TYPE_COLORS:
                link_type = "Other"
            
            # Create style URL based on type
            style_id = f"{link_type.replace(' ', '_').replace('-', '_')}_line"
            
            placemark = kml.Placemark(
                name=f"{link_dict['link_label']}",
                style_url=styles.StyleUrl(
                    url=(
                        "#los_line"
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

            # Add to the appropriate folder based on type
            if link_dict["is_los"]:
                los_folder.append(placemark)
            else:
                type_folders[link_type].append(placemark)

        # Generate the KML string
        kml_string = kml_root.to_string()
        
        # Insert LookAt element directly into the KML XML string to set the initial NYC view for tools such as Google Earth
        doc_pos = kml_string.find("<Document")
        if doc_pos != -1:
            doc_end_pos = kml_string.find(">", doc_pos)
            if doc_end_pos != -1:
                # Insert LookAt element after the Document opening tag
                lookat_xml = """
  <LookAt>
    <longitude>-73.9857</longitude>
    <latitude>40.7484</latitude>
    <altitude>0</altitude>
    <heading>0</heading>
    <tilt>0</tilt>
    <range>80000</range>
    <altitudeMode>relativeToGround</altitudeMode>
  </LookAt>"""
                kml_string = kml_string[:doc_end_pos+1] + lookat_xml + kml_string[doc_end_pos+1:]
        
        return HttpResponse(
            kml_string,
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
