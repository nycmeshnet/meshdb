import datetime
import logging
import re
from typing import List, Optional

from django.db.models import Q

from meshapi.models import LOS, Device, Link, Node, Sector
from meshapi.types.uisp_api.data_links import DataLink as UISPDataLink
from meshapi.types.uisp_api.devices import Device as UISPDevice
from meshapi.util.uisp_import.constants import (
    DEFAULT_SECTOR_AZIMUTH,
    DEFAULT_SECTOR_RADIUS,
    DEFAULT_SECTOR_WIDTH,
    DEVICE_MODEL_TO_BEAM_WIDTH,
    DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS,
    EXCLUDED_UISP_DEVICE_CATEGORIES,
    NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME,
)
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links, get_uisp_session
from meshapi.util.uisp_import.update_objects import update_device_from_uisp_data, update_link_from_uisp_data
from meshapi.util.uisp_import.utils import (
    get_building_from_network_number,
    get_link_type,
    guess_compass_heading_from_device_name,
    notify_admins_of_changes,
    parse_uisp_datetime,
)


def import_and_sync_uisp_devices(uisp_devices: List[UISPDevice]) -> None:
    for uisp_device in uisp_devices:
        uisp_uuid = uisp_device["identification"]["id"]
        uisp_category = uisp_device["identification"]["category"]
        uisp_name = uisp_device["identification"]["name"]

        if uisp_category in EXCLUDED_UISP_DEVICE_CATEGORIES:
            logging.debug(
                f"During UISP device import, {uisp_name} "
                f'(UISP ID {uisp_uuid}) was skipped because the "{uisp_category}" has been '
                "excluded in meshapi.util.uisp_import.constants"
            )
            continue

        modified_name = uisp_device["identification"]["name"]
        for find, replace in DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS.items():
            modified_name = modified_name.replace(find, replace)

        network_number_matches = re.findall(NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME, modified_name)

        if not len(network_number_matches):
            logging.warning(
                f"During UISP device import, {uisp_name} (UISP ID {uisp_uuid}) was skipped "
                f"because the device name does not include anything that looks like a NN"
            )
            continue

        # Take the first network number we find, since additional network numbers usually
        # represent the other side of the link
        uisp_network_number = int(network_number_matches[0])

        try:
            uisp_node = Node.objects.get(network_number=uisp_network_number)
        except Node.DoesNotExist:
            logging.warning(
                f"During UISP device import, {uisp_name} (UISP ID {uisp_uuid}) was skipped "
                f"because the inferred NN ({uisp_network_number}) did not correspond to any "
                f"nodes in our database"
            )
            continue

        if not uisp_device["overview"]["status"]:
            # If UISP doesn't have a status value, assume active
            uisp_status = Device.DeviceStatus.ACTIVE
        elif uisp_device["overview"]["status"] == "active":
            uisp_status = Device.DeviceStatus.ACTIVE
        else:
            uisp_status = Device.DeviceStatus.INACTIVE

        uisp_last_seen = parse_uisp_datetime(uisp_device["overview"]["lastSeen"])

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

                if guessed_compass_heading:
                    azimuth_message = (
                        f"Guessed azimuth of {sector.azimuth} degrees from device name. "
                        f"Please provide a more accurate value if available"
                    )
                else:
                    azimuth_message = (
                        f"Azimuth defaulted to {sector.azimuth} degrees. Device name did not indicate "
                        f"a cardinal direction. Please provide a more accurate value if available"
                    )

                notify_admins_of_changes(
                    sector,
                    [
                        azimuth_message,
                        (
                            f"Guessed coverage width of {sector.width} degrees from device type. "
                            f"Please provide a more accurate value if available"
                        ),
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
        uisp_uuid = uisp_link["id"]
        if not uisp_link["from"]["device"]:
            logging.warning(
                f"During UISP link import link with UISP ID {uisp_uuid} was skipped "
                f"because the data in UISP does not indicate what device this link connects from"
            )
            continue

        uisp_from_device_uuid = uisp_link["from"]["device"]["identification"]["id"]
        try:
            uisp_from_device = Device.objects.get(uisp_id=uisp_from_device_uuid)
        except Device.DoesNotExist:
            logging.warning(
                f"During UISP link import link with UISP ID {uisp_uuid} was skipped "
                f"because the data in UISP references a 'from' device (UISP ID {uisp_from_device_uuid}) "
                f"which we do not have in our database (perhaps it was skipped at device import time?)"
            )
            continue

        if not uisp_link["to"]["device"]:
            logging.warning(
                f"During UISP link import link with UISP ID {uisp_uuid} was skipped "
                f"because the data in UISP does not indicate what device this link connects to"
            )
            continue

        uisp_to_device_uuid = uisp_link["to"]["device"]["identification"]["id"]
        try:
            uisp_to_device = Device.objects.get(uisp_id=uisp_to_device_uuid)
        except Device.DoesNotExist:
            logging.warning(
                f"During UISP link import link with UISP ID {uisp_uuid} was skipped "
                f"because the data in UISP references a 'to' device (UISP ID {uisp_to_device_uuid}) "
                f"which we do not have in our database (perhaps it was skipped at device import time?)"
            )
            continue

        if uisp_link["state"] == "active":
            uisp_status = Link.LinkStatus.ACTIVE
        else:
            uisp_status = Link.LinkStatus.INACTIVE

        uisp_link_type = get_link_type(uisp_link)

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

        if not from_building or not to_building:
            logging.warning(
                f"Found link: {link} (ID {link.id}) which appears to be missing a building on one or "
                f"both ends. Please make sure that the following NNs have buildings associated with "
                f"them {link.from_device.node.network_number} and {link.to_device.node.network_number}"
            )
            continue

        if from_building == to_building:
            # Continue silently, intra-building links are reasonably common
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
                analysis_date=link.last_functioning_date_estimate,
                notes=f"Created automatically from Link ID {link.id} ({str(link)})\n\n",
            )
            los.save()
        else:
            for existing_los in existing_los_objects:
                # Supersede manually annotated LOSes with their auto-generated counterparts,
                # once they come online as links
                if link.status == Link.LinkStatus.ACTIVE and existing_los.source == LOS.LOSSource.HUMAN_ANNOTATED:
                    existing_los.source = LOS.LOSSource.EXISTING_LINK

                # Keep the LOS analysis date accurate for all that come from existing links
                if existing_los.source == LOS.LOSSource.EXISTING_LINK and link.last_functioning_date_estimate:
                    existing_los.analysis_date = link.last_functioning_date_estimate

                existing_los.save()


def run_uisp_import() -> None:
    import_and_sync_uisp_devices(get_uisp_devices())
    import_and_sync_uisp_links(get_uisp_links())
    sync_link_table_into_los_objects()
