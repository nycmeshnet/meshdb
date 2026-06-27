import logging
import os
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast
from urllib.parse import urlparse

from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.http import HttpRequest, HttpResponse
from django.templatetags.static import static
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from fastkml import Data, ExtendedData, geometry, kml, styles
from fastkml.enums import AltitudeMode
from pygeoif import LineString, Point
from rest_framework import permissions
from rest_framework import status as http_status
from rest_framework.views import APIView

from meshapi.models import Install, Link, Node
from meshapi.views.geography import (
    DEFAULT_ALTITUDE,
    KML_CONTENT_TYPE,
    KML_CONTENT_TYPE_WITH_CHARSET,
    IgnoreClientContentNegotiation,
)

# Define node type colors
ACTIVE_COLOR = "#F82C55"
HUB_COLOR = "#5AC8FA"
STANDARD_COLOR = "#F82C55"
SUPERNODE_COLOR = "#297AFE"
POP_COLOR = "#F6BE00"
AP_COLOR = "#38E708"
REMOTE_COLOR = "#800080"
HUB_COLOR = "#5AC8FA"
PENDING_COLOR = "#FFFFFF"  # White for Pending nodes and Planned links

# Define link type colors
WDS_5_GHZ_LINK_TYPE = "WDS (5 GHz)"

LINK_TYPE_COLORS = {
    "Other": "#FFFFFF",
    "VPN": "#7F0093",
    WDS_5_GHZ_LINK_TYPE: "#293BFE",
    "5 GHz": "#2675f4",
    "6 GHz": "#26a2f4",
    "24 GHz": "#45dafc",
    "60 GHz": "#45fcf8",
    "70-80 GHz": "#45fcea",
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


def hex_to_kml_color(hex_color: str, alpha: int = 255) -> str:
    """Convert hex color (#RRGGBB) to KML color format (AABBGGRR)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"{alpha:02x}{b}{g}{r}"


def link_type_to_style_id(link_type: str) -> str:
    return f"{link_type.replace(' ', '_').replace('-', '_').replace('/', '_')}_line"


def get_kml_link_type(link: Link) -> str:
    raw_type = link.type

    # Group explicit WDS links into their own KML folder/style
    if raw_type == Link.LinkType.FIVE_GHZ_WDS:
        return WDS_5_GHZ_LINK_TYPE

    # Keep all non-WDS 5 GHz variants grouped as regular 5 GHz in KML
    if raw_type in {
        Link.LinkType.FIVE_GHZ_UNSPECIFIED,
        Link.LinkType.FIVE_GHZ_WLAN,
        Link.LinkType.FIVE_GHZ_AIRMAX,
    }:
        return Link.LinkType.FIVE_GHZ_UNSPECIFIED

    return raw_type or "Other"


logger = logging.getLogger(__name__)

DOT_ICON_PATH = "meshapi/kml-icons/dot-100.png"
DOT_FALLBACK_URL = "https://rubendax.com/img/dot-100.png"
KML_ICON_URL = os.environ.get("KML_ICON_URL")
KML_ICON_BASE_URL = os.environ.get("KML_ICON_BASE_URL") or os.environ.get("SITE_BASE_URL")
LOCAL_ONLY_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

LinkKMLDict = TypedDict(
    "LinkKMLDict",
    {
        "link_label": str,
        "from_coord": Tuple[float, float, float],
        "to_coord": Tuple[float, float, float],
        "extended_data": Dict[str, Any],
    },
)


def absolute_static_url(request: HttpRequest, static_path: str, fallback_url: str = DOT_FALLBACK_URL) -> str:
    try:
        if KML_ICON_URL:
            return KML_ICON_URL

        icon_url = static(static_path)
        # STATIC_URL is configured as "static/" in this project (no leading slash),
        # which can produce a path relative to the current request URL in KML.
        # Force root-relative URL before making it absolute.
        if not icon_url.startswith(("http://", "https://", "/")):
            icon_url = f"/{icon_url}"

        if KML_ICON_BASE_URL:
            resolved_url = f"{KML_ICON_BASE_URL.rstrip('/')}{icon_url}"
        else:
            resolved_url = request.build_absolute_uri(icon_url)

        parsed = urlparse(resolved_url)
        if parsed.hostname and parsed.hostname.lower() in LOCAL_ONLY_HOSTS:
            logger.warning(
                "Resolved KML icon URL points to local host (%s); using fallback URL instead", parsed.hostname
            )
            return fallback_url

        return resolved_url
    except Exception:
        logger.exception("Failed to build absolute static URL for %s; using fallback", static_path)
        return fallback_url


def create_placemark(
    identifier: str,
    point: Point,
    status: str,
    node_type: Optional[str] = None,
    node_name: Optional[str] = None,
    has_node: bool = True,
) -> kml.Placemark:
    # Determine the appropriate style based on node type
    if node_type in ["Hub", "Supernode", "POP", "AP", "Remote"]:
        style_map = {
            "Hub": "#hub_dot",
            "Supernode": "#blue_dot",
            "POP": "#yellow_dot",
            "AP": "#green_dot",
            "Remote": "#purple_dot",
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
        "name": node_name if node_name else (f"NN {identifier}" if has_node else f"Install {identifier}"),
        "nodeType": node_type or "Standard",  # Add node type to extended data
        "status": status,
        "id": identifier,
    }

    placemark.extended_data = ExtendedData(elements=[Data(name=key, value=val) for key, val in extended_data.items()])

    return placemark


LocationMapData = TypedDict(
    "LocationMapData",
    {
        "installs": List[Install],
        "node": Optional[Node],
        "active": bool,
        "pending": bool,
        "altitude": float,
        "roof_access": bool,
    },
)


class ActiveMeshKML(APIView):
    permission_classes = [permissions.AllowAny]
    content_negotiation_class = IgnoreClientContentNegotiation

    def prioritize_links(self, kml_links: List[LinkKMLDict]) -> List[LinkKMLDict]:
        # Define priority order (lower number = higher priority)
        priority_order = {
            "Fiber": 1,
            "Ethernet": 2,
            "70-80 GHz": 3,
            "60 GHz": 4,
            "24 GHz": 5,
            "6 GHz": 6,
            "5 GHz": 7,
            WDS_5_GHZ_LINK_TYPE: 8,
            "Other": 9,
            "VPN": 10,
        }

        # Group links by coordinates
        link_groups: Dict[Tuple[Tuple[float, float, float], Tuple[float, float, float]], List[LinkKMLDict]] = {}
        for link in kml_links:
            # Create canonical representation of coordinates
            # Sort coordinates to ensure consistent ordering regardless of from/to direction
            coords = sorted([link["from_coord"], link["to_coord"]])
            key: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = (coords[0], coords[1])

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
        summary="Generate a KML file which contains all active nodes and links on the mesh",
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

        # Use one high-resolution icon for all node styles and control visual size via scale.
        # This is rendered more consistently by KML clients than relying on PNG dimensions alone.
        base_dot_url = absolute_static_url(request, DOT_ICON_PATH)

        red_dot_url = base_dot_url
        hub_dot_url = base_dot_url
        blue_dot_url = base_dot_url
        yellow_dot_url = base_dot_url
        green_dot_url = base_dot_url
        purple_dot_url = base_dot_url

        red_dot = styles.Style(
            id="red_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(STANDARD_COLOR),
                    scale=0.5,
                    icon=styles.Icon(href=red_dot_url),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        blue_dot = styles.Style(
            id="blue_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(SUPERNODE_COLOR),
                    scale=1.0,
                    icon=styles.Icon(href=blue_dot_url),
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
                    scale=0.75,
                    icon=styles.Icon(href=hub_dot_url),
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
                    scale=0.5,
                    icon=styles.Icon(href=green_dot_url),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        yellow_dot = styles.Style(
            id="yellow_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(POP_COLOR),
                    scale=1.0,
                    icon=styles.Icon(href=yellow_dot_url),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        purple_dot = styles.Style(
            id="purple_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(REMOTE_COLOR),
                    scale=0.5,
                    icon=styles.Icon(href=purple_dot_url),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        # White dot style for Pending nodes
        white_dot_url = base_dot_url
        white_dot = styles.Style(
            id="white_dot",
            styles=[
                styles.IconStyle(
                    color=hex_to_kml_color(PENDING_COLOR),
                    scale=0.5,
                    icon=styles.Icon(href=white_dot_url),
                    hot_spot=styles.HotSpot(x=0.5, y=0.5, xunits=styles.Units.fraction, yunits=styles.Units.fraction),
                )
            ],
        )

        # White line style for Planned links
        white_line = styles.Style(
            id="white_line",
            styles=[
                styles.LineStyle(color=hex_to_kml_color(PENDING_COLOR), width=3),
                styles.PolyStyle(color="00000000", fill=False, outline=True),
            ],
        )

        # Create style definitions for each link type
        link_styles = []
        for link_type, color in LINK_TYPE_COLORS.items():
            link_styles.append(
                styles.Style(
                    id=link_type_to_style_id(link_type),
                    styles=[
                        styles.LineStyle(color=hex_to_kml_color(color), width=3),
                        styles.PolyStyle(color="00000000", fill=False, outline=True),
                    ],
                )
            )

        kml_document = kml.Document(
            ns,
            styles=[red_dot, blue_dot, hub_dot, green_dot, yellow_dot, purple_dot, white_dot, white_line] + link_styles,
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

        # Create a separate folder for Planned nodes
        planned_nodes_folder = kml.Folder(name="Planned Nodes")
        nodes_folder.append(planned_nodes_folder)

        links_folder = kml.Folder(name="Links")
        kml_document.append(links_folder)

        # Create type folders for links
        type_folders = {}
        for link_type in list(LINK_TYPE_COLORS.keys()):
            type_folders[link_type] = kml.Folder(name=link_type)
            links_folder.append(type_folders[link_type])

        # Create a separate folder for Planned links
        planned_links_folder = kml.Folder(name="Planned Links")
        links_folder.append(planned_links_folder)

        # Create a dictionary to map coordinates to installs and nodes
        location_map: Dict[Tuple[float, float], LocationMapData] = {}

        # First pass: group installs by location
        for install in (
            Install.objects.select_related("node", "building")
            .filter(
                Q(status__in=[Install.InstallStatus.ACTIVE, Install.InstallStatus.PENDING])
                & Q(building__longitude__isnull=False)
                & Q(building__latitude__isnull=False)
            )
            .order_by("install_number")
        ):
            # Create a location key based on coordinates
            # Prioritize node coordinates if available
            if install.node and install.node.latitude is not None and install.node.longitude is not None:
                location_key = (float(install.node.longitude), float(install.node.latitude))
                altitude = float(install.node.altitude or DEFAULT_ALTITUDE)
            else:
                location_key = (float(install.building.longitude), float(install.building.latitude))
                altitude = float(install.building.altitude or DEFAULT_ALTITUDE)

            # Initialize location entry if it doesn't exist
            if location_key not in location_map:
                location_map[location_key] = {
                    "installs": [],
                    "node": None,
                    "active": False,
                    "pending": False,
                    "altitude": altitude,
                    "roof_access": False,
                }

            # Add this install to the location
            location_map[location_key]["installs"].append(install)

            # Track if any install at this location is active
            if install.status == Install.InstallStatus.ACTIVE:
                location_map[location_key]["active"] = True

            # Track if any install at this location is pending
            if install.status == Install.InstallStatus.PENDING:
                location_map[location_key]["pending"] = True

            # Track if any install has roof access
            if install.roof_access:
                location_map[location_key]["roof_access"] = True

            # If this install has a node with a network number, store it
            if install.node and install.node.network_number:
                location_map[location_key]["node"] = install.node

        # Additional pass: add active and planned nodes that might not have installs
        for active_node in (
            Node.objects.filter(status__in=[Node.NodeStatus.ACTIVE, Node.NodeStatus.PLANNED])
            .filter(latitude__isnull=False)
            .filter(longitude__isnull=False)
        ):
            # Create a location key based on coordinates
            location_key = (float(active_node.longitude), float(active_node.latitude))

            # Initialize location entry if it doesn't exist
            if location_key not in location_map:
                location_map[location_key] = {
                    "installs": [],
                    "node": active_node,
                    "active": active_node.status == Node.NodeStatus.ACTIVE,
                    "pending": active_node.status == Node.NodeStatus.PLANNED,
                    "altitude": float(active_node.altitude or DEFAULT_ALTITUDE),
                    "roof_access": False,
                }
            else:
                # Update existing location with node information if not already set
                if not location_map[location_key]["node"]:
                    location_map[location_key]["node"] = active_node
                if active_node.status == Node.NodeStatus.ACTIVE:
                    location_map[location_key]["active"] = True
                if active_node.status == Node.NodeStatus.PLANNED:
                    location_map[location_key]["pending"] = True

        # Second pass: create one placemark per unique location
        for location, data in location_map.items():
            lon, lat = location
            installs = data["installs"]
            node = data["node"]
            is_active = data["active"]
            is_pending = data["pending"]
            altitude = data["altitude"]

            # Skip nodes that are neither active nor pending
            if not is_active and not is_pending:
                continue

            # Determine the primary identifier and properties for the placemark
            if node:
                # Prioritize network number (NN) as identifier
                identifier = str(node.network_number)
                node_type = node.type or "Standard"
                status = node.status
                node_name = node.name  # Get the colloquial name if available
                has_node = True
            else:
                # Use the first install as the primary if no node exists
                identifier = f"#{installs[0].install_number}"
                node_type = installs[0].node.type if installs[0].node else "Standard"
                status = installs[0].status
                node_name = installs[0].node.name if installs[0].node else None  # Get the node name if available
                has_node = False

            # Get active and pending install numbers at this location
            active_installs = [install for install in installs if install.status == Install.InstallStatus.ACTIVE]
            pending_installs = [install for install in installs if install.status == Install.InstallStatus.PENDING]
            active_install_numbers = [str(install.install_number) for install in active_installs]
            pending_install_numbers = [str(install.install_number) for install in pending_installs]
            install_numbers = active_install_numbers + pending_install_numbers

            # Determine which folder and style to use
            # Pending nodes go to the Pending folder with white styling
            # Only if no active installs exist (active takes precedence)
            if is_pending and not is_active:
                folder = planned_nodes_folder
                style_url_value = "#white_dot"
            else:
                # Determine which folder to use based on node type
                folder = node_type_folders.get(node_type, node_type_folders["Standard"])
                # Determine the appropriate style based on node type
                if node_type in ["Hub", "Supernode", "POP", "AP", "Remote"]:
                    style_map = {
                        "Hub": "#hub_dot",
                        "Supernode": "#blue_dot",
                        "POP": "#yellow_dot",
                        "AP": "#green_dot",
                        "Remote": "#purple_dot",
                    }
                    style_url_value = style_map.get(node_type, "#red_dot")
                else:
                    style_url_value = "#red_dot"  # Standard node

            # Create the placemark
            placemark = create_placemark(
                identifier,
                Point(lon, lat, altitude),
                status,
                node_type,
                node_name,
                has_node,
            )

            # Override style for pending nodes
            if is_pending:
                placemark.style_url = styles.StyleUrl(url=style_url_value)

            placemark_extended_data = placemark.extended_data
            if placemark_extended_data is None:
                placemark_extended_data = ExtendedData(elements=[])
                placemark.extended_data = placemark_extended_data

            # Add install numbers to the extended data
            placemark_extended_data.elements.append(Data(name="install_numbers", value=",".join(install_numbers)))

            # Add the total count of active installs
            placemark_extended_data.elements.append(Data(name="install_count", value=str(len(install_numbers))))

            # Add install_date if available (from the earliest active install)
            if active_installs:
                # Get the earliest install_date from active installs
                install_dates = [install.install_date for install in active_installs if install.install_date]
                if install_dates:
                    earliest_install_date = min(install_dates)
                    placemark_extended_data.elements.append(
                        Data(name="install_date", value=earliest_install_date.isoformat())
                    )

            # Add to the appropriate folder
            folder.append(placemark)

        kml_links: List[LinkKMLDict] = []
        for link in (
            Link.objects.select_related("from_device__node", "to_device__node")
            .filter(status__in=[Link.LinkStatus.ACTIVE, Link.LinkStatus.PLANNED])  # Include active and planned links
            .filter(from_device__node__network_number__isnull=False)
            .filter(to_device__node__network_number__isnull=False)
            .filter(from_device__node__latitude__isnull=False)
            .filter(from_device__node__longitude__isnull=False)
            .filter(to_device__node__latitude__isnull=False)
            .filter(to_device__node__longitude__isnull=False)
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

            # Skip links where from and to nodes are the same (zero length)
            if from_identifier == to_identifier:
                continue

            kml_links.append(
                {
                    "link_label": link_label,
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
                        "type": get_kml_link_type(link),
                        "raw_type": link.type,
                        "status": link.status,
                        "from": str(from_identifier),
                        "to": str(to_identifier),
                        "install_date": link.install_date.isoformat() if link.install_date else None,
                    },
                }
            )

        # Prioritize links to show higher frequency links when there are duplicates
        kml_links = self.prioritize_links(kml_links)

        for link_dict in kml_links:
            # Determine link type
            link_type_value = link_dict["extended_data"].get("type")
            link_type = link_type_value if isinstance(link_type_value, str) else "Other"
            if link_type not in LINK_TYPE_COLORS:
                link_type = "Other"

            # Determine if this is a Planned link
            link_status = link_dict["extended_data"].get("status", "")
            is_planned = link_status == Link.LinkStatus.PLANNED

            # Planned links go to the Planned Links folder with white styling
            if is_planned:
                target_folder = planned_links_folder
                style_url_value = "#white_line"
            else:
                # Create style URL based on type
                style_id = link_type_to_style_id(link_type)
                style_url_value = f"#{style_id}"
                target_folder = type_folders[link_type]

            placemark = kml.Placemark(
                name=f"{link_dict['link_label']}",
                style_url=styles.StyleUrl(url=style_url_value),
                kml_geometry=geometry.LineString(
                    geometry=LineString([link_dict["from_coord"], link_dict["to_coord"]]),
                    altitude_mode=AltitudeMode.absolute,
                    extrude=True,
                ),
            )

            placemark.extended_data = ExtendedData(
                elements=[Data(name=key, value=val) for key, val in link_dict["extended_data"].items()]
            )

            # Add to the appropriate folder
            target_folder.append(placemark)

        # Generate the KML string
        kml_string = kml_root.to_string()

        # Insert LookAt element directly into the KML XML string
        # to set the initial NYC view for tools such as Google Earth
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
                kml_string = kml_string[: doc_end_pos + 1] + lookat_xml + kml_string[doc_end_pos + 1 :]

        return HttpResponse(
            kml_string,
            content_type=KML_CONTENT_TYPE_WITH_CHARSET,
            status=http_status.HTTP_200_OK,
        )
