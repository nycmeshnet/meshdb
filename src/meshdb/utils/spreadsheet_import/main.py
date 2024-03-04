import logging
import os
import sys
import time
from collections import defaultdict
from typing import List

import django

from meshdb.utils.spreadsheet_import import logger

logger.configure()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()

from meshapi import models
from meshdb.utils.spreadsheet_import.building.resolve_address import AddressParser
from meshdb.utils.spreadsheet_import.csv_load import (
    DroppedModification,
    SpreadsheetLinkStatus,
    SpreadsheetSectorStatus,
    get_spreadsheet_links,
    get_spreadsheet_rows,
    get_spreadsheet_sectors,
    print_dropped_edit_report,
    print_failure_report,
)
from meshdb.utils.spreadsheet_import.parse_building import get_or_create_building
from meshdb.utils.spreadsheet_import.parse_install import get_or_create_install
from meshdb.utils.spreadsheet_import.parse_link import create_link
from meshdb.utils.spreadsheet_import.parse_member import get_or_create_member
from meshdb.utils.spreadsheet_import.parse_sector import create_sector


def main():
    if len(sys.argv) != 4:
        print("Usage: meshdb-spreadsheet-import [Path to Form Responses CSV] [Path to Links CSV] [Path to Sectors CSV]")
        return

    if len(models.Member.objects.all()) != 0 or len(models.Building.objects.all()) != 0:
        logging.error(
            "Expected database to be empty before ingesting from spreadsheet data. "
            "Check that the DB is empty (python src/manage.py flush) and try again"
        )
        sys.exit(1)

    form_responses_path, links_path, sectors_path = sys.argv[1:4]

    rows, skipped = get_spreadsheet_rows(form_responses_path)
    logging.info(f'Loaded {len(rows)} rows from "{form_responses_path}"')

    member_duplicate_counts = defaultdict(lambda: 1)

    addr_parser = AddressParser()

    dropped_modifications: List[DroppedModification] = []

    max_install_num = max(row.id for row in rows)

    start_time = time.time()
    logging.info(f"Processing install # {rows[0].id}/{max_install_num}...")
    try:
        for i, row in enumerate(rows):
            if (i + 2) % 100 == 0:
                logging.info(
                    f"Processing install # {row.id}/{max_install_num}... "
                    f"({int(time.time() - start_time)} seconds elapsed)"
                )

            member, new = get_or_create_member(row, dropped_modifications.append)
            if not new:
                member_duplicate_counts[member.primary_email_address] += 1

            building = get_or_create_building(row, addr_parser, dropped_modifications.append)
            if not building:
                skipped[row.id] = "Unable to parse address"
                continue

            install = get_or_create_install(row)

            install.building = building
            install.member = member

            building_status_for_current_row = (
                models.Building.BuildingStatus.ACTIVE
                if install.status == models.Install.InstallStatus.ACTIVE
                else models.Building.BuildingStatus.INACTIVE
            )

            if not building.building_status:
                # If this is a new building, just use the new status
                building.building_status = building_status_for_current_row
            else:
                # If this building already exists and is ACTIVE, don't touch it since there's
                # an active install for another row tied to it
                # However if it's INACTIVE, there's a chance this row is an active install which
                # would make the building active, so use the new status
                if building.building_status == models.Building.BuildingStatus.INACTIVE:
                    building.building_status = building_status_for_current_row

            member.save()
            building.save()
            install.save()

        logging.debug("Top 15 duplicate emails and submission counts:")
        for email, count in sorted(member_duplicate_counts.items(), key=lambda item: item[1], reverse=True)[:15]:
            logging.debug(f"{email}: {count}")
    except BaseException as e:
        if isinstance(e, KeyboardInterrupt):
            logging.error("Received keyboard interrupt, exiting early...")
        if not isinstance(e, KeyboardInterrupt):
            raise e
        sys.exit(1)
    finally:
        # Always print the failure report on our way out, even if we're interrupted
        print_failure_report(skipped, form_responses_path)
        print_dropped_edit_report(dropped_modifications, form_responses_path)

    logging.info(f"Loading links from '{links_path}'...")
    links = get_spreadsheet_links(links_path)
    for spreadsheet_link in links:
        link = create_link(spreadsheet_link)
        if link:
            link.save()

    logging.info(f"Loading sectors from '{sectors_path}'...")
    sectors = get_spreadsheet_sectors(sectors_path)
    for spreadsheet_sector in sectors:
        sector = create_sector(spreadsheet_sector)
        if sector:
            sector.save()


if __name__ == "__main__":
    main()
