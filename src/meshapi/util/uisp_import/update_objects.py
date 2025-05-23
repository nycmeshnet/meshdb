import datetime
import logging
from typing import List, Optional

import requests
from drf_hooks.signals import hook_event

from meshapi.models import Device, Link, Node
from meshapi.util.uisp_import.constants import (
    UISP_ABANDON_DATE_AGE_BEFORE_WARNING_ABOUT_REACTIVATION,
    UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE,
)
from meshapi.util.uisp_import.utils import get_uisp_link_last_seen


def update_device_from_uisp_data(
    existing_device: Device,
    uisp_node: Node,
    uisp_name: str,
    uisp_status: Device.DeviceStatus,
    uisp_last_seen: Optional[datetime.datetime],
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

    fire_device_deactivated_hook = False
    if existing_device.status != uisp_status:
        if uisp_status == Device.DeviceStatus.INACTIVE:
            # We wait 30 days to make sure this device is actually inactive,
            # and not just temporarily offline
            if uisp_last_seen is None or (
                (datetime.datetime.now(datetime.timezone.utc) - uisp_last_seen)
                > UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE
            ):
                change_message = f"Marked as {Device.DeviceStatus.INACTIVE} due to it being offline in UISP"
                if uisp_last_seen:
                    existing_device.abandon_date = uisp_last_seen.date()
                    change_message += (
                        " for more than "
                        f"{int(UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE.total_seconds() / 60 / 60 / 24)} days"
                    )
                fire_device_deactivated_hook = True

                existing_device.status = Device.DeviceStatus.INACTIVE
                change_messages.append(change_message)

        if uisp_status == Device.DeviceStatus.ACTIVE:
            existing_device.status = Device.DeviceStatus.ACTIVE

            change_message = f"Marked as {Device.DeviceStatus.ACTIVE} due to it coming back online in UISP"
            if (
                existing_device.abandon_date
                and datetime.date.today() - existing_device.abandon_date
                > UISP_ABANDON_DATE_AGE_BEFORE_WARNING_ABOUT_REACTIVATION
            ):
                change_message += (
                    ". Warning: this device was previously abandoned on "
                    f"{existing_device.abandon_date.isoformat()}, if this device has been re-purposed, "
                    "please make sure the device name and network number are updated to reflect the new location "
                    "and function"
                )

            existing_device.abandon_date = None
            change_messages.append(change_message)

    if (
        existing_device.status == Device.DeviceStatus.INACTIVE
        and existing_device.abandon_date is None
        and uisp_last_seen is not None
    ):
        existing_device.abandon_date = uisp_last_seen.date()
        change_messages.append(f"Added missing abandon date of {existing_device.abandon_date} based on UISP last-seen")

    # Only update the device if we actually changed anything to avoid making
    # duplicate entries
    if change_messages:
        existing_device.save()

    if fire_device_deactivated_hook:
        hook_event.send(
            sender=existing_device.__class__,
            action="uisp-deactivated",
            instance=existing_device,
        )

    return change_messages


def update_link_from_uisp_data(
    existing_link: Link,
    uisp_link_id: str,
    uisp_from_device: Device,
    uisp_to_device: Device,
    uisp_status: Link.LinkStatus,
    uisp_session: Optional[requests.Session] = None,
) -> List[str]:
    change_messages = []

    # We can't add change messages because they're super spammy,
    # so use this to determine if we should save when changing the uisp_id.
    uisp_link_id_changed = False

    if uisp_link_id != existing_link.uisp_id:
        existing_link.uisp_id = uisp_link_id
        logging.info(
            f"Changed UISP link ID to {uisp_link_id} for {existing_link} link (ID {existing_link.id}). "
            f"This is likely due to a UISP UUID rotation"
        )
        uisp_link_id_changed = True

    uisp_device_pair = {uisp_to_device, uisp_from_device}
    db_device_pair = {existing_link.from_device, existing_link.to_device}

    if uisp_device_pair != db_device_pair:
        uisp_device_pair_str = "[" + ", ".join(sorted(str(dev) for dev in uisp_device_pair)) + "]"
        db_device_pair_str = "[" + ", ".join(sorted(str(dev) for dev in db_device_pair)) + "]"
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
            if uisp_last_seen is None or (
                (datetime.datetime.now(datetime.timezone.utc) - uisp_last_seen)
                > UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE
            ):
                change_message = f"Marked as {Link.LinkStatus.INACTIVE} due to it being offline in UISP"

                if uisp_last_seen:
                    existing_link.abandon_date = uisp_last_seen.date()
                    change_message += (
                        " for more than "
                        f"{int(UISP_OFFLINE_DURATION_BEFORE_MARKING_INACTIVE.total_seconds() / 60 / 60 / 24)} days"
                    )

                existing_link.status = Link.LinkStatus.INACTIVE
                change_messages.append(change_message)

        if uisp_status == Link.LinkStatus.ACTIVE:
            existing_link.status = Link.LinkStatus.ACTIVE
            change_message = f"Marked as {Link.LinkStatus.ACTIVE} due to it coming back online in UISP"
            existing_link.abandon_date = None
            change_messages.append(change_message)

    if (
        existing_link.status == Link.LinkStatus.INACTIVE
        and existing_link.abandon_date is None
        and uisp_last_seen is not None
    ):
        existing_link.abandon_date = uisp_last_seen.date()
        change_messages.append(f"Added missing abandon date of {existing_link.abandon_date} based on UISP last-seen")

    # Only save the object if there actually are change_messages, otherwise don't
    # to avoid creating an unnecessary object.
    if change_messages or uisp_link_id_changed:
        existing_link.save()
    return change_messages
