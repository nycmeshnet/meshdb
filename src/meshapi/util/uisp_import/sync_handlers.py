import datetime
import logging
import re
from typing import List

from django.db import transaction
from django.db.models import Q

from meshapi.admin import downclass_device
from meshapi.models import LOS, Device, Link, Node, Sector
from meshapi.serializers import DeviceSerializer, LinkSerializer
from meshapi.types.uisp_api.data_links import DataLink as UISPDataLink
from meshapi.types.uisp_api.devices import Device as UISPDevice
from meshapi.util.admin_notifications import notify_administrators_of_data_issue
from meshapi.util.uisp_import.constants import (
    DEFAULT_SECTOR_AZIMUTH,
    DEFAULT_SECTOR_RADIUS,
    DEFAULT_SECTOR_WIDTH,
    DEVICE_MODEL_TO_BEAM_WIDTH,
    DEVICE_NAME_NETWORK_NUMBER_SUBSTITUTIONS,
    EXCLUDED_UISP_DEVICE_CATEGORIES,
    NETWORK_NUMBER_REGEX_FOR_DEVICE_NAME,
)
from meshapi.util.uisp_import.fetch_uisp import get_uisp_session
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

        # If UISP doesn't have a status value, assume active
        if not uisp_device["overview"]["status"] or uisp_device["overview"]["status"] == "active":
            uisp_status = Device.DeviceStatus.ACTIVE
        else:
            uisp_status = Device.DeviceStatus.INACTIVE

        uisp_last_seen = (
            parse_uisp_datetime(uisp_device["overview"]["lastSeen"]) if uisp_device["overview"]["lastSeen"] else None
        )

        # This block guards against most duplication by checking uisp-uuid against
        # the uisp-uuids we already know about.
        # Further avoidance of saving historical records is done in the update function
        with transaction.atomic():
            existing_devices: List[Device] = list(Device.objects.filter(uisp_id=uisp_uuid).select_for_update())
            if existing_devices:
                if len(existing_devices) > 1:
                    notify_administrators_of_data_issue(
                        [downclass_device(device) for device in existing_devices],
                        DeviceSerializer,
                        message=f"Possible duplicate objects detected, devices "
                        f"share the same UISP ID ({uisp_uuid})",
                    )

                for existing_device in existing_devices:
                    change_list = update_device_from_uisp_data(
                        existing_device,
                        uisp_node,
                        uisp_name,
                        uisp_status,
                        uisp_last_seen,
                    )
                    if change_list:
                        notify_admins_of_changes(existing_device, change_list)
                continue

        device_fields = {
            "node": uisp_node,
            "name": uisp_name,
            "uisp_id": uisp_uuid,
            "status": uisp_status,
            "install_date": parse_uisp_datetime(uisp_device["overview"]["createdAt"]).date(),
            "abandon_date": (
                uisp_last_seen.date() if uisp_last_seen and uisp_status == Device.DeviceStatus.INACTIVE else None
            ),
            "notes": f"Automatically imported from UISP on {datetime.date.today().isoformat()}\n\n",
        }

        if uisp_device["identification"]["type"] == "airMax" and uisp_device["overview"]["wirelessMode"] == "ap-ptmp":
            try:
                guessed_compass_heading = guess_compass_heading_from_device_name(uisp_name)
            except ValueError:
                logging.exception("Invalid device name detected")
                guessed_compass_heading = None

            guessed_beam_width = DEVICE_MODEL_TO_BEAM_WIDTH.get(
                uisp_device["identification"]["model"], DEFAULT_SECTOR_WIDTH
            )

            # Only when we're sure the sector doesn't exist do we save it
            # XXX (wdn): is this the only place we try to save sectors in here?
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

    with transaction.atomic():
        for device in Device.objects.filter(uisp_id__isnull=False):
            uisp_uuid_set = {uisp_device["identification"]["id"] for uisp_device in uisp_devices}

            if device.uisp_id and device.uisp_id not in uisp_uuid_set and device.status != Device.DeviceStatus.INACTIVE:
                # If this device has been removed from UISP, mark it as inactive
                device.status = Device.DeviceStatus.INACTIVE
                device.save()

                notify_admins_of_changes(
                    device,
                    [
                        "Marked as inactive because there is no corresponding device in UISP, "
                        "it was probably deleted there",
                    ],
                )


def import_and_sync_uisp_links(uisp_links: List[UISPDataLink]) -> None:
    uisp_session = get_uisp_session()
    uisp_uuid_set = {uisp_link["id"] for uisp_link in uisp_links}

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

        with transaction.atomic():
            existing_links: List[Link] = list(Link.objects.filter(uisp_id=uisp_uuid).select_for_update())

            if len(existing_links) > 1:
                notify_administrators_of_data_issue(
                    existing_links,
                    LinkSerializer,
                    message=f"Possible duplicate objects detected, links share the same UISP ID ({uisp_uuid})",
                )

            # XXX (wdn): Do we want to make a history record in this case? I _think_ so?
            # maybe i dont understand this well enough
            if not existing_links:
                # Under some circumstances, UISP randomly changes the internal ID it uses for
                # ethernet link objects. We attempt to detect that here, by finding existing MeshDB
                # links that connect the same devices as the seemingly "new" link
                #
                # This is trickier than it may seem, since there are valid situations where a pair
                # of devices can have multiple links for redundancy and bandwidth (e.g. S16 <-> Core LACP)
                # We exclude these cases by only looking for "lost" MeshDB link objects which think
                # they have a corresponding UISP link but don't, since this indicates a high likelihood
                # of an ID change
                existing_links = list(
                    Link.objects.filter(
                        (
                            Q(from_device=uisp_from_device, to_device=uisp_to_device)
                            | Q(from_device=uisp_to_device, to_device=uisp_from_device)
                        )
                        & Q(uisp_id__isnull=False)
                        & ~Q(uisp_id="")
                        & ~Q(uisp_id__in=uisp_uuid_set)
                    ).select_for_update()
                )

                if len(existing_links) > 1:
                    notify_administrators_of_data_issue(
                        existing_links,
                        LinkSerializer,
                        message=f"Possible duplicate objects detected, links share the same device pair "
                        f"({uisp_from_device.name} & {uisp_to_device.name}), but are orphaned from their UISP data, "
                        f"so we cannot tell if they are actually redundant physical links",
                    )

            if existing_links:
                for existing_link in existing_links:
                    change_list = update_link_from_uisp_data(
                        existing_link,
                        uisp_uuid,
                        uisp_from_device,
                        uisp_to_device,
                        uisp_status,
                        uisp_session,
                    )
                    if change_list:
                        notify_admins_of_changes(existing_link, change_list)
                continue

        # By now, we're reasonably sure the link doesn't exist, so go ahead and
        # create it.
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

        if uisp_link_type == Link.LinkType.ETHERNET:
            notify_admins_of_changes(
                link,
                [
                    f"Used link type of '{uisp_link_type}' from UISP metadata, however this may not be correct in the "
                    f"case of VPN or Fiber links. Please provide a more accurate value if available"
                ],
                created=True,
            )

    with transaction.atomic():
        for link in Link.objects.filter(uisp_id__isnull=False):
            if link.uisp_id and link.uisp_id not in uisp_uuid_set and link.status == Link.LinkStatus.ACTIVE:
                # If this link has been removed from UISP, mark it as inactive
                link.status = Link.LinkStatus.INACTIVE
                link.save()

                notify_admins_of_changes(
                    link,
                    [
                        "Marked as inactive because there is no corresponding link in UISP, "
                        "it was probably deleted there",
                    ],
                )


def sync_link_table_into_los_objects() -> None:
    for link in (
        Link.objects.exclude(type=Link.LinkType.ETHERNET)
        .exclude(type=Link.LinkType.FIBER)
        .exclude(type=Link.LinkType.VPN)
    ):
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

        with transaction.atomic():
            existing_los_objects = LOS.objects.filter(
                Q(from_building=from_building, to_building=to_building)
                | Q(from_building=to_building, to_building=from_building)
            ).select_for_update()

            if len(existing_los_objects):
                for existing_los in existing_los_objects:
                    # Keep track of whether or not we actually changed anything,
                    # so that we don't unnecessarily save later.
                    changed_los = False

                    # Supersede manually annotated LOSes with their auto-generated counterparts,
                    # once they come online as links
                    if link.status == Link.LinkStatus.ACTIVE and existing_los.source == LOS.LOSSource.HUMAN_ANNOTATED:
                        existing_los.source = LOS.LOSSource.EXISTING_LINK
                        changed_los = True

                    # Keep the LOS analysis date accurate for all that come from existing links
                    if (
                        existing_los.source == LOS.LOSSource.EXISTING_LINK
                        and link.last_functioning_date_estimate
                        and existing_los.analysis_date != link.last_functioning_date_estimate
                    ):
                        existing_los.analysis_date = link.last_functioning_date_estimate
                        changed_los = True

                    if changed_los:
                        print("changed los")
                        existing_los.save()
                continue

        # At this point, we're reasonably sure the LOS does not exist, so go ahead
        # and create a new one.
        los = LOS(
            from_building=from_building,
            to_building=to_building,
            source=LOS.LOSSource.EXISTING_LINK,
            analysis_date=link.last_functioning_date_estimate,
            notes=f"Created automatically from Link ID {link.id} ({str(link)})\n\n",
        )
        los.save()
