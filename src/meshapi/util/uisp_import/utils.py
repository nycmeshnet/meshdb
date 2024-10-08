import datetime
import math
from typing import List, Optional, Type, Union

import dateutil.parser
import requests
from rest_framework.serializers import Serializer

from meshapi.admin import downclass_device
from meshapi.models import AccessPoint, Building, Device, Link, Node, Sector
from meshapi.serializers import AccessPointSerializer, DeviceSerializer, LinkSerializer, SectorSerializer
from meshapi.types.uisp_api.data_links import DataLink as USIPDataLink
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.uisp_import.fetch_uisp import get_uisp_device_detail, get_uisp_session


def parse_uisp_datetime(datetime_str: str) -> datetime.datetime:
    return dateutil.parser.isoparse(datetime_str)


def get_link_type(uisp_link: USIPDataLink) -> Link.LinkType:
    if uisp_link["type"] == "wireless":
        if uisp_link["frequency"]:
            if uisp_link["frequency"] < 7_000:
                return Link.LinkType.FIVE_GHZ
            elif uisp_link["frequency"] < 40_000:
                return Link.LinkType.TWENTYFOUR_GHZ
            elif uisp_link["frequency"] < 70_000:
                return Link.LinkType.SIXTY_GHZ

            return Link.LinkType.SEVENTY_EIGHTY_GHZ

        return Link.LinkType.FIVE_GHZ
    elif uisp_link["type"] == "ethernet":
        return Link.LinkType.ETHERNET
    elif uisp_link["type"] == "pon":
        return Link.LinkType.FIBER

    raise ValueError(f"Unexpected UISP link type: {uisp_link['type']} for link {uisp_link['id']}")


def get_building_from_network_number(network_number: Optional[int]) -> Optional[Building]:
    if not network_number:
        return None

    node = Node.objects.get(network_number=network_number)

    # We need to lookup which buildings have this NN as primary
    # in the case of multiple buildings, we resolve arbitrarily to the lower ID one
    building_candidate = Building.objects.filter(primary_node=node).order_by("id").first()

    # If none of the buildings have this as a primary node, maybe one has it as a secondary node?
    if not building_candidate:
        building_candidate = Building.objects.filter(nodes=node).order_by("id").first()

    # Okay we did our best, return the building if we have it, or None if we don't
    return building_candidate


def get_uisp_link_last_seen(
    from_device_uuid: str, to_device_uuid: str, uisp_session: Optional[requests.Session] = None
) -> Optional[datetime.datetime]:
    if not uisp_session:
        uisp_session = get_uisp_session()

    from_device_uisp_dict = get_uisp_device_detail(from_device_uuid, uisp_session)
    to_device_uisp_dict = get_uisp_device_detail(to_device_uuid, uisp_session)

    last_seen_times = [
        parse_uisp_datetime(date_str)
        for date_str in [from_device_uisp_dict["overview"]["lastSeen"], to_device_uisp_dict["overview"]["lastSeen"]]
        if date_str is not None
    ]

    return min(last_seen_times) if last_seen_times else None


def get_serializer(db_object: Union[Device, Link, Sector, AccessPoint]) -> Type[Serializer]:
    serializer_lookup = {
        Device: DeviceSerializer,
        Sector: SectorSerializer,
        AccessPoint: AccessPointSerializer,
        Link: LinkSerializer,
    }
    return serializer_lookup[type(db_object)]


def notify_admins_of_changes(
    db_object: Union[Device, Link, Sector, AccessPoint],
    change_list: List[str],
    created: bool = False,
) -> None:
    # Attempt to downclass if needed (so admin links and such make sense)
    # We hide the model inheritance from admins, so they'd be confused if
    # we called a Sector a "device" in a notification message
    # (also the admin UI link would be wrong from their perspective)
    if type(db_object) is Device:
        db_object = downclass_device(db_object)

    if created:
        message = (
            f"created {db_object._meta.verbose_name} based on information from UISP. "
            f"The following items may require attention:\n" + "\n".join(" - " + change for change in change_list)
        )
    else:
        message = (
            f"modified {db_object._meta.verbose_name} based on information from UISP. "
            f"The following changes were made:\n"
            + "\n".join(" - " + change for change in change_list)
            + "\n(to prevent this, make changes to these fields in UISP rather than directly in MeshDB)"
        )

    notify_administrators_of_data_issue(
        [db_object],
        get_serializer(db_object),
        message=message,
    )


def guess_compass_heading_from_device_name(device_name: str) -> Optional[float]:
    contributors = []

    s2o2 = math.sqrt(2) / 2
    cardinal_directions = {
        "northeast": (s2o2, s2o2),
        "southeast": (s2o2, -s2o2),
        "southwest": (-s2o2, -s2o2),
        "northwest": (-s2o2, s2o2),
        "north": (0, 1),
        "south": (0, -1),
        "east": (1, 0),
        "west": (-1, 0),
    }

    mutated_device_name = device_name.lower()
    for direction, coordinate_pair in cardinal_directions.items():
        if direction in mutated_device_name:
            mutated_device_name = mutated_device_name.replace(direction, "", 1)
            contributors.append(coordinate_pair)

    if not len(contributors):
        # If we don't get any signal from this device name,
        # tell the caller that we couldn't guess
        return None

    coord = tuple(sum(x) for x in zip(*contributors))

    if math.sqrt(coord[0] ** 2 + coord[1] ** 2) < 1:
        raise ValueError(
            f"Invalid device name {device_name}, does this result in a sensible "
            f"cardinal direction? Combining oposite cardinal directions like "
            f"'northsouth' or 'eastwest' is not permitted"
        )

    # Negative sign and plus 90 degrees is used to convert from standard
    # "mathematical" (counter-clockwise degrees from the positive x-axis) to
    # "compass heading" (clockwise degrees from the positive y-axis)
    return round(-math.degrees(math.atan2(coord[1], coord[0])) + 90, 1) % 360
