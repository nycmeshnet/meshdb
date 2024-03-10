from typing import Dict

from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.http import HttpResponse
from fastkml import Data, ExtendedData, geometry, kml, styles
from fastkml.enums import AltitudeMode
from pygeoif import LineString, Point
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes

from meshapi.models import Building, Install, Link

KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml; charset=utf-8"
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


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def map_kml(request):
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
        styles=[styles.LineStyle(color="ff0000ff", width=2), styles.PolyStyle(color="00000000")],
    )

    grey_line = styles.Style(
        id="grey_line",
        styles=[styles.LineStyle(color="ffcccccc", width=2), styles.PolyStyle(color="00000000")],
    )

    kml_document = kml.Document(ns, styles=[grey_dot, red_dot, red_line, grey_line])
    kml_root.append(kml_document)

    nodes_folder = kml.Folder(name="Nodes")
    kml_document.append(nodes_folder)

    links_folder = kml.Folder(name="Links")
    kml_document.append(links_folder)

    folder_map: Dict[str, kml.Folder] = {}

    for city_name, folder_name in CITY_FOLDER_MAP.items():
        folder_map[city_name] = kml.Folder(name=folder_name)
        nodes_folder.append(folder_map[city_name])

    for install in Install.objects.filter(
        ~Q(status=Install.InstallStatus.CLOSED)
        & Q(building__longitude__isnull=False)
        & Q(building__latitude__isnull=False)
    ):
        identifier = install.via_device.get().network_number or install.install_number
        placemark = kml.Placemark(
            name=str(identifier),
            style_url=styles.StyleUrl(
                url="#red_dot" if install.status == Install.InstallStatus.ACTIVE else "#grey_dot"
            ),
            kml_geometry=geometry.Point(
                geometry=Point(
                    install.building.longitude,
                    install.building.latitude,
                    install.building.altitude or DEFAULT_ALTITUDE,
                ),
                altitude_mode=AltitudeMode.absolute,
            ),
        )

        extended_data = {
            "name": str(identifier),
            "roofAccess": str(install.roof_access),
            "marker-color": ACTIVE_COLOR if install.status == Install.InstallStatus.ACTIVE else INACTIVE_COLOR,
            "id": str(identifier),
            "install_number": str(install.install_number),
            "network_number": str(install.via_device.get().network_number),
            "status": install.status,
            # Leave disabled, notes can leak a lot of information & this endpoint is public
            # "notes": install.notes,
        }

        placemark.extended_data = ExtendedData(
            elements=[Data(name=key, value=val) for key, val in extended_data.items()]
        )
        folder = folder_map[install.building.city if install.building.city in folder_map.keys() else None]
        folder.append(placemark)

    for link in (
        Link.objects.filter(~Q(status=Link.LinkStatus.DEAD))
        .annotate(
            highest_altitude=Greatest(
                "from_device__powered_by_install__building__altitude",
                "to_device__powered_by_install__building__altitude",
            )
        )
        .order_by(F("highest_altitude").asc(nulls_first=True))
    ):
        placemark = kml.Placemark(
            name=f"Links-{link.id}",
            style_url=styles.StyleUrl(url="#red_line" if link.status == Link.LinkStatus.ACTIVE else "#grey_line"),
            kml_geometry=geometry.LineString(
                geometry=LineString(
                    [
                        (
                            link.from_device.powered_by_install.building.longitude,
                            link.from_device.powered_by_install.building.latitude,
                            link.from_device.powered_by_install.building.altitude or DEFAULT_ALTITUDE,
                        ),
                        (
                            link.to_device.powered_by_install.building.longitude,
                            link.to_device.powered_by_install.building.latitude,
                            link.to_device.powered_by_install.building.altitude or DEFAULT_ALTITUDE,
                        ),
                    ]
                ),
                altitude_mode=AltitudeMode.absolute,
                extrude=True,
            ),
        )

        from_identifier = (
            link.from_device.network_number
            or link.from_device.powered_by_install.building.installs.first().install_number
        )
        to_identifier = (
            link.to_device.network_number or link.to_device.powered_by_install.building.installs.first().install_number
        )

        extended_data = {
            "name": f"Links-{link.id}",
            "stroke": ACTIVE_COLOR if link.status == Link.LinkStatus.ACTIVE else INACTIVE_COLOR,
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
        links_folder.append(placemark)

    return HttpResponse(
        kml_root.to_string(),
        content_type=KML_CONTENT_TYPE,
        status=status.HTTP_200_OK,
    )
