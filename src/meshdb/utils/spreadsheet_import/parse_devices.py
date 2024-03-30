import datetime
import logging
import os
import re
from collections import defaultdict
from typing import List, Optional

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()


import dateutil.parser

from meshapi.models import Device, Install, Node, Sector
from meshdb.utils.spreadsheet_import.csv_load import (
    SpreadsheetRow,
    SpreadsheetSector,
    SpreadsheetSectorStatus,
    SpreadsheetStatus,
    get_spreadsheet_rows,
    get_spreadsheet_sectors,
)
from meshdb.utils.spreadsheet_import.fetch_uisp import download_uisp_devices

nn_subsitutions = {
    "sn1": "227",
    "supernode1": "227",
    "375p": "227",
    "sn3": "713",
}


def find_uisp_device_with_ssid(devices: List[dict], ssid: str):
    for i, uisp_dev in enumerate(devices):
        if uisp_dev["attributes"] and uisp_dev["attributes"].get("ssid") == ssid:
            return uisp_dev, i

    return None, None


def find_uisp_device_with_name(devices: List[dict], name: str):
    for i, uisp_dev in enumerate(devices):
        if uisp_dev["identification"]["name"] and uisp_dev["identification"]["name"] == name:
            return uisp_dev, i

    return None, None


def find_uisp_omni(devices: List[dict]):
    for i, uisp_dev in enumerate(devices):
        if uisp_dev["identification"]["name"] and "-omni" in uisp_dev["identification"]["name"]:
            return uisp_dev, i

    return None, None


def parse_uisp_datetime(datetime_str: str) -> datetime.date:
    return dateutil.parser.isoparse(datetime_str).date()


def create_device(nn: int, uisp_device: dict, spreadsheet_sector: Optional[SpreadsheetSector]):
    try:
        node = Node.objects.get(network_number=nn)
    except Node.DoesNotExist:
        logging.error(f'Could not find Node for NN {nn} while loading device: {uisp_device["identification"]["name"]}')
        return

    uisp_model = uisp_device["identification"]["model"]
    if uisp_model == "UNKNOWN":
        uisp_model = uisp_device["identification"]["modelName"]

    if len(Device.objects.filter(uisp_id=uisp_device["identification"]["id"])):
        logging.warning(
            f'Skipping creation of duplicate device with UISP ID {uisp_device["identification"]["id"]} '
            f'({uisp_device["identification"]["name"]})'
        )
        return

    uisp_ip_addresses = list(
        set(
            addr.split("/")[0]
            for addr in uisp_device["ipAddressList"] + [uisp_device["ipAddress"]]
            if addr and not addr.startswith("169") and not addr.startswith("192")
        )
    )
    uisp_ip_address = uisp_ip_addresses[0] if uisp_ip_addresses else None
    if uisp_ip_addresses[1:]:
        logging.warning(
            f"Discarding IP addresses: {uisp_ip_addresses[1:]} for UISP device: "
            f"{uisp_device['identification']['name']}"
        )

    if spreadsheet_sector:
        if not uisp_model:
            uisp_model = spreadsheet_sector.device

        sector_notes = "\n".join([spreadsheet_sector.notes, spreadsheet_sector.comments]).strip()

        if spreadsheet_sector.status == SpreadsheetSectorStatus.active:
            status = Device.DeviceStatus.ACTIVE
        elif spreadsheet_sector.status == SpreadsheetSectorStatus.abandoned:
            status = Device.DeviceStatus.INACTIVE
        elif spreadsheet_sector.status == SpreadsheetSectorStatus.potential:
            status = Device.DeviceStatus.POTENTIAL
        else:
            raise ValueError(f"Invalid spreadsheet sector status {spreadsheet_sector.status}")

        device = Sector(
            node=node,
            name=uisp_device["identification"]["name"],
            uisp_id=uisp_device["identification"]["id"],
            model=uisp_model,
            type=uisp_device["identification"]["role"],
            ip_address=uisp_ip_address,
            status=status,
            latitude=node.latitude,
            longitude=node.longitude,
            altitude=node.altitude,
            radius=spreadsheet_sector.radius,
            azimuth=spreadsheet_sector.azimuth,
            width=spreadsheet_sector.width,
            ssid=spreadsheet_sector.ssid,
            install_date=spreadsheet_sector.install_date,
            abandon_date=spreadsheet_sector.abandon_date,
            notes=sector_notes if sector_notes else None,
        )
    else:
        if not uisp_model:
            uisp_model = "Unknown"

        if not uisp_device["overview"]["status"]:
            # If UISP doesn't have a status value, assume active
            status = Device.DeviceStatus.ACTIVE
        elif uisp_device["overview"]["status"] == "active":
            status = Device.DeviceStatus.ACTIVE
        else:
            status = Device.DeviceStatus.INACTIVE

        device = Device(
            node=node,
            name=uisp_device["identification"]["name"],
            uisp_id=uisp_device["identification"]["id"],
            model=uisp_model,
            type=uisp_device["identification"]["role"],
            ip_address=uisp_ip_address,
            status=status,
            latitude=node.latitude,
            longitude=node.longitude,
            altitude=node.altitude,
            install_date=parse_uisp_datetime(uisp_device["overview"]["createdAt"]),
            abandon_date=(
                parse_uisp_datetime(uisp_device["overview"]["lastSeen"])
                if status == Device.DeviceStatus.INACTIVE
                else None
            ),
            notes=None,
        )

    device.save()


def load_devices_supplement_with_uisp(spreadsheet_sectors: List[SpreadsheetSector]):
    uisp_devices = download_uisp_devices()

    grouped_by_nn = defaultdict(lambda: {"uisp": [], "spreadsheet": []})

    for sector in spreadsheet_sectors:
        grouped_by_nn[int(sector.node_id)]["spreadsheet"].append(sector)

    for uisp_device in uisp_devices:
        if uisp_device["identification"]["category"] == "optical" or not uisp_device["identification"]["name"]:
            continue

        nn_regex = r"\b\d{1,4}\b"

        modified_name = uisp_device["identification"]["name"]
        for find, replace in nn_subsitutions.items():
            modified_name = modified_name.replace(find, replace)

        nn_matches = re.findall(nn_regex, modified_name)
        if len(nn_matches):
            grouped_by_nn[int(nn_matches[0])]["uisp"].append(uisp_device)
        else:
            logging.error(f'Couldn\'t find NN in device named: {uisp_device["identification"]["name"]}')

    for nn, devices in grouped_by_nn.items():
        matches = []

        unmatched_spreadsheet = []
        matched_uisp_ids = []

        for spreadsheet_dev in devices["spreadsheet"]:
            if spreadsheet_dev.ssid:
                match, i = find_uisp_device_with_ssid(devices["uisp"], spreadsheet_dev.ssid)
                if match:
                    matches.append((spreadsheet_dev, match))
                    matched_uisp_ids.append(i)
                    continue

                match, i = find_uisp_device_with_name(devices["uisp"], spreadsheet_dev.ssid)
                if match:
                    matches.append((spreadsheet_dev, match))
                    matched_uisp_ids.append(i)
                    continue

            if spreadsheet_dev.device == "Omni":
                match, i = find_uisp_omni(devices["uisp"])
                if match:
                    matches.append((spreadsheet_dev, match))
                    matched_uisp_ids.append(i)
                    continue

            # If we didn't hit a continue, track that this device isn't yet matched
            unmatched_spreadsheet.append(spreadsheet_dev)

        unmatched_uisp = [uisp_dev for i, uisp_dev in enumerate(devices["uisp"]) if i not in matched_uisp_ids]

        for spreadsheet_dev, uisp_dev in matches:
            create_device(nn, uisp_dev, spreadsheet_dev)

        for uisp_dev in unmatched_uisp:
            create_device(nn, uisp_dev, None)

        active_spreadsheet_discards = sum(
            1 for spreadsheet_dev in unmatched_spreadsheet if spreadsheet_dev.status == SpreadsheetSectorStatus.active
        )
        if active_spreadsheet_discards:
            logging.warning(
                f"Discarding information for {active_spreadsheet_discards} unmatched spreadsheet rows for NN {nn}"
            )


def load_access_points(spreadsheet_installs: List[SpreadsheetRow]):
    for row in spreadsheet_installs:
        if "AP" in row.notes:
            node = Install.objects.get(install_number=row.id).node

            ap_device = Device(
                node=node,
                name=f"{row.nodeName} AP" if row.nodeName else "AP",
                model="Unknown",
                type=Device.DeviceType.AP,
                status=Device.DeviceStatus.ACTIVE
                if row.status == SpreadsheetStatus.installed
                else Device.DeviceStatus.INACTIVE,
                latitude=row.latitude,
                longitude=row.longitude,
                install_date=row.installDate,
                abandon_date=row.abandonDate,
                notes=f"Spreadsheet Notes:\n{row.notes}\n{row.notes2}\n{row.installNotes}\n"
                f"Location: {row.apartment}\n"
                f"Name: {row.nodeName}\n",
            )
            ap_device.save()


if __name__ == "__main__":
    load_devices_supplement_with_uisp(
        get_spreadsheet_sectors("spreadsheet_data/New Node Form (Responses) - Sectors.csv")
    )
