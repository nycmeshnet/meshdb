import logging
from typing import Callable, Optional, Tuple

import geopy.distance

from meshapi import models
from meshapi.exceptions import AddressError
from meshapi.models import Building
from meshdb.utils.spreadsheet_import.building.constants import INVALID_BIN_NUMBERS, AddressTruthSource, DatabaseAddress
from meshdb.utils.spreadsheet_import.building.resolve_address import AddressParser
from meshdb.utils.spreadsheet_import.csv_load import DroppedModification, SpreadsheetRow

SAME_BUILDING_MAX_SEPARATION_SQUARE_RADIUS = (
    0.000018  # ~1.5 meters at NYC lat - https://en.wikipedia.org/wiki/Decimal_degrees#Precision
)


def get_existing_building(
    bin_number: Optional[int], db_addr: DatabaseAddress, lat_lon: Tuple[float, float]
) -> Optional[Building]:

    if bin_number and db_addr.street_address:
        existing_buildings = models.Building.objects.filter(
            bin=bin_number,
            street_address=db_addr.street_address,
        )
        if len(existing_buildings) > 0:
            if len(existing_buildings) > 1:
                logging.error(
                    f"Found more than one building with BIN: {bin_number} and "
                    f"street address {db_addr.street_address}! These should have been de-duplicated"
                )
            return existing_buildings[0]
    else:
        existing_buildings = models.Building.objects.filter(
            latitude__in=(
                lat_lon[0] - SAME_BUILDING_MAX_SEPARATION_SQUARE_RADIUS,
                lat_lon[0] + SAME_BUILDING_MAX_SEPARATION_SQUARE_RADIUS,
            ),
            longitude__in=(
                lat_lon[1] - SAME_BUILDING_MAX_SEPARATION_SQUARE_RADIUS,
                lat_lon[1] + SAME_BUILDING_MAX_SEPARATION_SQUARE_RADIUS,
            ),
        )
        if len(existing_buildings) > 0:
            if len(existing_buildings) > 1:
                logging.error(
                    f"Found more than one building stacked at the coordinates: {lat_lon}!"
                    f" These should have been de-duplicated"
                )
            return existing_buildings[0]
    return None


def diff_new_building_against_existing(
    row_id: int,
    existing_building: models.Building,
    new_building: models.Building,
    add_dropped_edit: Callable[[DroppedModification], None],
) -> str:
    diff_notes = ""
    if existing_building.bin != new_building.bin and new_building.bin:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_building.installs.all()),
                row_id,
                existing_building.street_address,
                "building.bin",
                str(existing_building.bin) if existing_building.bin else "",
                str(new_building.bin),
            )
        )
        logging.debug(
            f"Dropping changed BIN from install # {row_id} "
            f"{repr(existing_building.bin)} -> {repr(new_building.bin)}"
        )
        diff_notes += f"\nDropped BIN change from install #{row_id}: {new_building.bin}"

    if existing_building.street_address != new_building.street_address and new_building.street_address:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_building.installs.all()),
                row_id,
                str(existing_building.bin) if existing_building.bin else existing_building.street_address,
                "building.street_address",
                existing_building.street_address if existing_building.street_address else "",
                new_building.street_address,
            )
        )
        logging.debug(
            f"Dropping changed street address from install # {row_id} "
            f"{repr(existing_building.street_address)} -> {repr(new_building.street_address)}"
        )
        diff_notes += f"\nDropped address change from install #{row_id}: {new_building.street_address}"

    if existing_building.city != new_building.city and new_building.city:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_building.installs.all()),
                row_id,
                str(existing_building.bin) if existing_building.bin else existing_building.street_address,
                "building.city",
                existing_building.city if existing_building.city else "",
                new_building.city,
            )
        )
        logging.debug(
            f"Dropping changed city from install # {row_id} "
            f"{repr(existing_building.city)} -> {repr(new_building.city)}"
        )
        diff_notes += f"\nDropped city change from install #{row_id}: {new_building.city}"

    if existing_building.state != new_building.state and new_building.state:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_building.installs.all()),
                row_id,
                str(existing_building.bin) if existing_building.bin else existing_building.street_address,
                "building.state",
                existing_building.state if existing_building.state else "",
                new_building.state,
            )
        )
        logging.debug(
            f"Dropping changed state from install # {row_id} "
            f"{repr(existing_building.state)} -> {repr(new_building.state)}"
        )
        diff_notes += f"\nDropped state change from install #{row_id}: {new_building.state}"

    if existing_building.zip_code != new_building.zip_code and new_building.zip_code:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_building.installs.all()),
                row_id,
                str(existing_building.bin) if existing_building.bin else existing_building.street_address,
                "building.zip_code",
                existing_building.zip_code if existing_building.zip_code else "",
                new_building.zip_code,
            )
        )
        logging.debug(
            f"Dropping changed zip code from install # {row_id} "
            f"{repr(existing_building.zip_code)} -> {repr(new_building.zip_code)}"
        )
        diff_notes += f"\nDropped ZIP change from install #{row_id}: {new_building.zip_code}"

    return diff_notes


def get_or_create_building(
    row: SpreadsheetRow,
    address_parser: Optional[AddressParser] = None,
    add_dropped_edit: Optional[Callable[[DroppedModification], None]] = None,
) -> Optional[models.Building]:
    dob_bin = row.bin if row.bin and row.bin > 0 and row.bin not in INVALID_BIN_NUMBERS else None

    if not address_parser:
        address_parser = AddressParser()

    if not add_dropped_edit:
        # Use a no-op function if our caller doesn't specify a destination
        # for dropped edits, to avoid runtime errors
        add_dropped_edit = lambda x: None

    try:
        address_result = address_parser.parse_address(row, add_dropped_edit)
    except AddressError as e:
        return None

    distance_warning = ""
    if address_result.discovered_lat_lon:
        error_vs_google = geopy.distance.geodesic(address_result.discovered_lat_lon, (row.latitude, row.longitude)).m
        if error_vs_google > 100:
            add_dropped_edit(
                DroppedModification(
                    [row.id],
                    row.id,
                    address_result.discovered_bin
                    if address_result.discovered_bin
                    else address_result.address.street_address,
                    "lat_long_discrepancy_vs_spreadsheet",
                    str(address_result.discovered_lat_lon),
                    str((row.latitude, row.longitude)),
                )
            )
            distance_warning = (
                f"WARNING: Mismatch vs spreadsheet lat/lon {str((row.latitude, row.longitude))} "
                f"of {error_vs_google} meters\n"
            )
            logging.debug(
                f"Mismatch vs spreadsheet of {error_vs_google} meters for address '{row.address}'"
                f" for install # {row.id}. Wrong borough or city? We think this address is in "
                f"{address_result.address.city}, {address_result.address.state}"
            )

    latitude = row.latitude
    longitude = row.longitude
    altitude = (
        # TODO: Change this to match new DOB ID if changed from spreadsheet?
        #  Would require another API call
        row.altitude
        if row.altitude and row.altitude >= 0
        else None
    )

    existing_building = get_existing_building(
        address_result.discovered_bin or dob_bin, address_result.address, (latitude, longitude)
    )
    if existing_building:
        diff_notes = diff_new_building_against_existing(
            row.id,
            existing_building,
            models.Building(
                bin=address_result.discovered_bin or dob_bin,
                street_address=address_result.address.street_address,
                city=address_result.address.city,
                state=address_result.address.state,
                zip_code=address_result.address.zip_code,
            ),
            add_dropped_edit,
        )

        if diff_notes:
            if not existing_building.notes:
                existing_building.notes = ""

            existing_building.notes += diff_notes

        return existing_building

    addr_truth_sources = (
        [source.value for source in address_result.truth_sources] if address_result.truth_sources else None
    )
    return Building(
        bin=address_result.discovered_bin or dob_bin,
        street_address=address_result.address.street_address,
        city=address_result.address.city,
        state=address_result.address.state,
        zip_code=address_result.address.zip_code,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        address_truth_sources=addr_truth_sources,
        # Let's not throw away the spreadsheet location information, just case it's useful in
        # chasing down a mis-parsed address in the future
        notes=f"Spreadsheet Address: {row.address}\n"
        f"Spreadsheet Neighborhood: {row.neighborhood}\n"
        f"Spreadsheet BIN: {dob_bin}\n\n"
        f"Our Expected Coordinates (from {addr_truth_sources}): {address_result.discovered_lat_lon}\n"
        f"{distance_warning}",
    )
