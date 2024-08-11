import datetime
from typing import List, Optional

import requests

from meshapi.models import Device, Link, Node
from meshapi.util.uisp_import.utils import get_uisp_link_last_seen

OFFLINE_DURATION_BEFORE_INACTIVE = datetime.timedelta(days=30)


def update_device_from_uisp_data(
    existing_device: Device,
    uisp_node: Node,
    uisp_name: str,
    uisp_status: Device.DeviceStatus,
    uisp_last_seen: datetime.datetime,
) -> List[str]:
    change_messages = []

    if existing_device.name != uisp_name:
        change_messages.append(f'Changed name from "{existing_device.name}" to "{uisp_name}"')
        existing_device.name = uisp_name

    if existing_device.node != uisp_node:
        change_messages.append(
            f"Changed network number from {existing_device.node.network_number} to {uisp_node.network_number}"
        )
        existing_device.node = uisp_node

    if existing_device.status != uisp_status:
        if uisp_status == Device.DeviceStatus.INACTIVE:
            # We wait 30 days to make sure this device is actually inactive,
            # and not just temporarily offline
            if (datetime.datetime.now(datetime.timezone.utc) - uisp_last_seen) > OFFLINE_DURATION_BEFORE_INACTIVE:
                existing_device.abandon_date = uisp_last_seen.date()
                existing_device.status = Device.DeviceStatus.INACTIVE

                change_messages.append(
                    f"Marked as {Device.DeviceStatus.INACTIVE} due to being offline "
                    f"for more than {int(OFFLINE_DURATION_BEFORE_INACTIVE.total_seconds() / 60 / 60 / 24)} days"
                )

        if uisp_status == Device.DeviceStatus.ACTIVE:
            existing_device.status = Device.DeviceStatus.ACTIVE

            change_message = f"Marked as {Device.DeviceStatus.ACTIVE} due to coming back online in UISP"
            if existing_device.abandon_date:
                change_message += (
                    ". Warning: this device was previously abandoned on "
                    f"{existing_device.abandon_date.isoformat()}, if this device has been re-purposed, "
                    "please make sure the device name and network number are updated to reflect the new location "
                    "and function"
                )
                existing_device.abandon_date = None

            change_messages.append(change_message)

    if existing_device.status == Device.DeviceStatus.INACTIVE and existing_device.abandon_date is None:
        existing_device.abandon_date = uisp_last_seen.date()
        change_messages.append(f"Added missing abandon date of {existing_device.abandon_date} based on UISP last-seen")

    existing_device.save()
    return change_messages


def update_link_from_uisp_data(
    existing_link: Link,
    uisp_from_device: Device,
    uisp_to_device: Device,
    uisp_status: Link.LinkStatus,
    uisp_link_type: Link.LinkType,
    uisp_session: Optional[requests.Session] = None,
) -> List[str]:
    change_messages = []

    uisp_device_pair = {uisp_to_device, uisp_from_device}
    db_device_pair = {existing_link.from_device, existing_link.to_device}

    if uisp_device_pair != db_device_pair:
        uisp_device_pair_str = "[" + ", ".join(str(dev) for dev in uisp_device_pair) + "]"
        db_device_pair_str = "[" + ", ".join(str(dev) for dev in db_device_pair) + "]"
        change_messages.append(f"Changed connected device pair from {db_device_pair_str} to {uisp_device_pair_str}")
        existing_link.from_device = uisp_from_device
        existing_link.to_device = uisp_to_device

    # This call gives a mypy error because uisp_from_device.uisp_id and uisp_to_device.uisp_id are technically
    # optional on the Device type. However, we obtained these objects by querying on these fields so we know this
    # is always safe
    uisp_last_seen = get_uisp_link_last_seen(
        uisp_from_device.uisp_id,  # type: ignore
        uisp_to_device.uisp_id,  # type: ignore
        uisp_session,
    )

    if existing_link.status != uisp_status:
        if uisp_status == Link.LinkStatus.INACTIVE:
            # We wait 30 days to make sure this link is actually inactive,
            # and not just temporarily offline
            if (datetime.datetime.now(datetime.timezone.utc) - uisp_last_seen) > OFFLINE_DURATION_BEFORE_INACTIVE:
                existing_link.abandon_date = uisp_last_seen.date()
                existing_link.status = Link.LinkStatus.INACTIVE

                change_messages.append(
                    f"Marked as {Link.LinkStatus.INACTIVE} due to being offline "
                    f"for more than {int(OFFLINE_DURATION_BEFORE_INACTIVE.total_seconds() / 60 / 60 / 24)} days"
                )

        if uisp_status == Link.LinkStatus.ACTIVE:
            existing_link.status = Link.LinkStatus.ACTIVE

            change_message = f"Marked as {Link.LinkStatus.ACTIVE} due to coming back online in UISP"
            if existing_link.abandon_date:
                change_message += (
                    ". Warning: this link was previously abandoned on "
                    f"{existing_link.abandon_date.isoformat()}, if this link has been re-purposed, "
                    "please make sure the device names and network numbers are updated to reflect the new location"
                )
                existing_link.abandon_date = None

            change_messages.append(change_message)

    if existing_link.type != uisp_link_type:
        change_messages.append(f"Changed link type from {existing_link.type} to {uisp_link_type}")
        existing_link.type = uisp_link_type

    if existing_link.status == Link.LinkStatus.INACTIVE and existing_link.abandon_date is None:
        existing_link.abandon_date = uisp_last_seen.date()
        change_messages.append(f"Added missing abandon date of {existing_link.abandon_date} based on UISP last-seen")

    existing_link.save()
    return change_messages
