import datetime
import logging
import re
from typing import List, Optional

from django.db.models import Q

from meshapi.models import LOS, Device, Link, Node, Sector
from meshapi.types.uisp_api.data_links import DataLink as UISPDataLink
from meshapi.types.uisp_api.devices import Device as UISPDevice
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links, get_uisp_session
from meshapi.util.uisp_import.update_objects import update_device_from_uisp_data, update_link_from_uisp_data
from meshapi.util.uisp_import.utils import (
    get_building_from_network_number,
    get_link_type,
    guess_compass_heading_from_device_name,
    notify_admins_of_changes,
    parse_uisp_datetime,
)

EXCLUDED_UISP_DEVICE_CATEGORIES = ["optical"]


DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS = {
    "sn1": "227",
    "supernode1": "227",
    "375p": "227",
    "sn3": "713",
}

NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME = r"\b\d{1,4}\b"

DEFAULT_SECTOR_AZIMUTH = 0  # decimal degrees (compass heading)
DEFAULT_SECTOR_WIDTH = 0  # decimal degrees
DEFAULT_SECTOR_RADIUS = 1  # km

DEVICE_MODEL_TO_BEAM_WIDTH = {
    "LAP-120": 120,
    "LAP-GPS": 120,
    "PS-5AC": 45,  # In reality this is based on the antenna used, this is just a guess based on our historical use
    "RP-5AC-Gen2": 90,  # In reality this is based on the antenna used, this is just a guess based on our historical use
}


def import_and_sync_uisp_devices(uisp_devices: List[UISPDevice]) -> None:
    for uisp_device in uisp_devices:
        if uisp_device["identification"]["category"] in EXCLUDED_UISP_DEVICE_CATEGORIES:
            # TODO Better error?
            continue

        uisp_name = uisp_device["identification"]["name"]
        modified_name = uisp_device["identification"]["name"]
        for find, replace in DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS.items():
            modified_name = modified_name.replace(find, replace)

        network_number_matches = re.findall(NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME, modified_name)

        if not len(network_number_matches):
            # TODO Better error
            logging.error(f"Couldn't find NN in device named: {uisp_name}")
            continue

        # Take the first network number we find, since additional network numbers usually
        # represent the other side of the link
        uisp_network_number = int(network_number_matches[0])

        try:
            uisp_node = Node.objects.get(network_number=uisp_network_number)
        except Node.DoesNotExist:
            # TODO Better error
            logging.error(f"Could not find Node for NN {uisp_network_number} while loading device: " f"{uisp_name}")
            continue

        if not uisp_device["overview"]["status"]:
            # If UISP doesn't have a status value, assume active
            uisp_status = Device.DeviceStatus.ACTIVE
        elif uisp_device["overview"]["status"] == "active":
            uisp_status = Device.DeviceStatus.ACTIVE
        else:
            uisp_status = Device.DeviceStatus.INACTIVE

        uisp_last_seen = parse_uisp_datetime(uisp_device["overview"]["lastSeen"])

        uisp_uuid = uisp_device["identification"]["id"]

        existing_device: Optional[Device] = Device.objects.filter(uisp_id=uisp_uuid).first()

        if existing_device:
            change_list = update_device_from_uisp_data(
                existing_device,
                uisp_node,
                uisp_name,
                uisp_status,
                uisp_last_seen,
            )
            if change_list:
                notify_admins_of_changes(existing_device, change_list)
        else:
            device_fields = {
                "node": uisp_node,
                "name": uisp_name,
                "uisp_id": uisp_uuid,
                "status": uisp_status,
                "install_date": parse_uisp_datetime(uisp_device["overview"]["createdAt"]).date(),
                "abandon_date": uisp_last_seen.date() if uisp_status == Device.DeviceStatus.INACTIVE else None,
                "notes": f"Automatically imported from UISP on {datetime.date.today().isoformat()}\n\n",
            }

            if (
                uisp_device["identification"]["type"] == "airMax"
                and uisp_device["overview"]["wirelessMode"] == "ap-ptmp"
            ):
                try:
                    guessed_compass_heading = guess_compass_heading_from_device_name(uisp_name)
                except ValueError:
                    logging.exception("Invalid device name detected")
                    guessed_compass_heading = None

                guessed_beam_width = DEVICE_MODEL_TO_BEAM_WIDTH.get(
                    uisp_device["identification"]["model"], DEFAULT_SECTOR_WIDTH
                )

                sector = Sector(
                    **device_fields,
                    azimuth=guessed_compass_heading or DEFAULT_SECTOR_AZIMUTH,
                    width=guessed_beam_width,
                    radius=DEFAULT_SECTOR_RADIUS,
                )
                sector.save()

                notify_admins_of_changes(
                    sector,
                    [
                        f"Guessed azimuth of {sector.azimuth} degrees from device name. Please provide a more accurate value if available",
                        f"Guessed coverage width of {sector.width} degrees from device type. Please provide a more accurate value if available",
                        f"Set default radius of {sector.radius} km. Please correct if this is not accurate",
                    ],
                    created=True,
                )
            else:
                device = Device(**device_fields)
                device.save()


def import_and_sync_uisp_links(uisp_links: List[UISPDataLink]) -> None:
    uisp_session = get_uisp_session()
    for uisp_link in uisp_links:
        try:
            if not uisp_link["from"]["device"]:
                # TODO Better error?
                continue

            uisp_from_device = Device.objects.get(uisp_id=uisp_link["from"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            # TODO Better error
            logging.warning(
                f"Skipping UISP link because device "
                f"{uisp_link['from']['device']['identification']['name']} could not be found"
            )
            continue

        try:
            if not uisp_link["to"]["device"]:
                # TODO Better error?
                continue

            uisp_to_device = Device.objects.get(uisp_id=uisp_link["to"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            # TODO Better error
            logging.warning(
                f"Skipping UISP link because device "
                f"{uisp_link['to']['device']['identification']['name']} could not be found"
            )
            continue

        if uisp_link["state"] == "active":
            uisp_status = Link.LinkStatus.ACTIVE
        else:
            uisp_status = Link.LinkStatus.INACTIVE

        uisp_link_type = get_link_type(uisp_link)

        uisp_uuid = uisp_link["id"]
        existing_link: Optional[Link] = Link.objects.filter(uisp_id=uisp_uuid).first()
        if existing_link:
            change_list = update_link_from_uisp_data(
                existing_link,
                uisp_from_device,
                uisp_to_device,
                uisp_status,
                uisp_link_type,
                uisp_session,
            )
            if change_list:
                notify_admins_of_changes(existing_link, change_list)
        else:
            link = Link(
                from_device=uisp_from_device,
                to_device=uisp_to_device,
                status=uisp_status,
                type=uisp_link_type,
                uisp_id=uisp_uuid,
                notes=f"Automatically imported from UISP on {datetime.date.today().isoformat()}\n\n",
                # UISP doesn't track the following info
                install_date=None,
                abandon_date=None,
                description=None,
            )
            link.save()


def sync_link_table_into_los_objects() -> None:
    for link in Link.objects.all():
        from_building = get_building_from_network_number(link.from_device.node.network_number)
        to_building = get_building_from_network_number(link.to_device.node.network_number)

        if not from_building or not to_building or from_building == to_building:
            # TODO: Log something here
            continue

        existing_los_objects = LOS.objects.filter(
            Q(from_building=from_building, to_building=to_building)
            | Q(from_building=to_building, to_building=from_building)
        )

        if not len(existing_los_objects):
            los = LOS(
                from_building=from_building,
                to_building=to_building,
                source=LOS.LOSSource.EXISTING_LINK,
                analysis_date=link.abandon_date
                if link.status == Link.LinkStatus.INACTIVE and link.abandon_date
                else datetime.date.today(),
                notes=f"Created automatically from Link ID {link.id} ({str(link)})\n\n",
            )
            los.save()
        else:
            for existing_los in existing_los_objects:
                if link.status == Link.LinkStatus.ACTIVE:
                    if existing_los.source == LOS.LOSSource.HUMAN_ANNOTATED:
                        existing_los.source = LOS.LOSSource.EXISTING_LINK

                    if existing_los.source == LOS.LOSSource.EXISTING_LINK:
                        existing_los.analysis_date = datetime.date.today()

                elif link.status == Link.LinkStatus.INACTIVE and link.abandon_date:
                    if existing_los.source == LOS.LOSSource.EXISTING_LINK:
                        existing_los.analysis_date = link.abandon_date

                existing_los.save()


def run_uisp_import() -> None:
    import_and_sync_uisp_devices(get_uisp_devices())
    import_and_sync_uisp_links(get_uisp_links())
    sync_link_table_into_los_objects()
