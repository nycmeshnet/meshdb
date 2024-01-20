import logging
import os
import sys
import time
from collections import defaultdict
from typing import List

import django
from django.db.models import Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()

from meshapi import models
from meshdb.utils.spreadsheet_import import logger
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
from meshdb.utils.spreadsheet_import.parse_member import get_or_create_member


def main():
    logger.configure()
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
                member_duplicate_counts[member.email_address] += 1

            building = get_or_create_building(row, addr_parser, dropped_modifications.append)
            if not building:
                skipped[row.id] = "Unable to parse address"
                continue

            install = get_or_create_install(row)

            install.building = building
            install.member = member

            building_status_for_current_row = (
                models.Building.BuildingStatus.ACTIVE
                if install.install_status == models.Install.InstallStatus.ACTIVE
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
        return
    finally:
        # Always print the failure report on our way out, even if we're interrupted
        print_failure_report(skipped, form_responses_path)
        print_dropped_edit_report(dropped_modifications, form_responses_path)

    logging.info(f"Loading links from '{links_path}'...")
    links = get_spreadsheet_links(links_path)
    for spreadsheet_link in links:
        try:
            from_building = models.Building.objects.get(
                install__install_number=spreadsheet_link.from_install_num,
            )
            to_building = models.Building.objects.get(
                install__install_number=spreadsheet_link.to_install_num,
            )
        except models.Building.DoesNotExist:
            message = (
                f"Could not find building for install {spreadsheet_link.from_install_num} or "
                f"{spreadsheet_link.to_install_num}"
            )
            if spreadsheet_link.status != SpreadsheetLinkStatus.dead:
                raise ValueError(message)
            else:
                logging.warning(message + ". But this link is dead, skipping this spreadsheet row")
                continue

        if spreadsheet_link.status in [
            SpreadsheetLinkStatus.vpn,
            SpreadsheetLinkStatus.active,
            SpreadsheetLinkStatus.sixty_ghz,
            SpreadsheetLinkStatus.fiber,
        ]:
            status = models.Link.LinkStatus.ACTIVE
        elif spreadsheet_link.status == SpreadsheetLinkStatus.dead:
            status = models.Link.LinkStatus.DEAD
        elif spreadsheet_link.status == SpreadsheetLinkStatus.planned:
            status = models.Link.LinkStatus.PLANNED
        else:
            raise ValueError(f"Invalid spreadsheet link status {spreadsheet_link.status}")

        link_type = None
        if spreadsheet_link.status in [
            SpreadsheetLinkStatus.active,
        ]:
            link_type = models.Link.LinkType.STANDARD
        elif spreadsheet_link.status == SpreadsheetLinkStatus.vpn:
            link_type = models.Link.LinkType.VPN
        elif spreadsheet_link.status == SpreadsheetLinkStatus.sixty_ghz:
            link_type = models.Link.LinkType.MMWAVE

        link = models.Link(
            from_building=from_building,
            to_building=to_building,
            status=status,
            type=link_type,
            install_date=spreadsheet_link.install_date,
            abandon_date=spreadsheet_link.abandon_date,
            description=spreadsheet_link.where_to_where,
            notes="\n".join([spreadsheet_link.notes, spreadsheet_link.comments]),
        )
        link.save()

    logging.info(f"Loading sectors from '{sectors_path}'...")
    sectors = get_spreadsheet_sectors(sectors_path)
    for spreadsheet_sector in sectors:
        try:
            building = models.Building.objects.filter(
                Q(install__install_number=spreadsheet_sector.node_id) | Q(primary_nn=spreadsheet_sector.node_id),
            )[0]
        except IndexError:
            message = f"Could not find building for install {spreadsheet_sector.node_id}"
            if spreadsheet_sector.status != SpreadsheetSectorStatus.abandoned:
                raise ValueError(message)
            else:
                logging.warning(message + ". But this sector is abandoned, skipping this spreadsheet row")

        if spreadsheet_sector.status == SpreadsheetSectorStatus.active:
            status = models.Sector.SectorStatus.ACTIVE
        elif spreadsheet_sector.status == SpreadsheetSectorStatus.abandoned:
            status = models.Sector.SectorStatus.ABANDONED
        elif spreadsheet_sector.status == SpreadsheetSectorStatus.potential:
            status = models.Sector.SectorStatus.POTENTIAL
        else:
            raise ValueError(f"Invalid spreadsheet sector status {spreadsheet_sector.status}")

        sector = models.Sector(
            building=building,
            radius=spreadsheet_sector.radius,
            azimuth=spreadsheet_sector.azimuth,
            width=spreadsheet_sector.width,
            status=status,
            install_date=spreadsheet_sector.install_date,
            abandon_date=spreadsheet_sector.abandon_date,
            device_name=spreadsheet_sector.device,
            name=spreadsheet_sector.names,
            ssid=spreadsheet_sector.ssid,
            notes="\n".join([spreadsheet_sector.notes, spreadsheet_sector.comments]),
        )
        sector.save()


if __name__ == "__main__":
    main()
