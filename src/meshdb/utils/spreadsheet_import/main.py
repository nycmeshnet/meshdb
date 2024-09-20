import logging
import os
import sys
import time
from collections import defaultdict
from typing import Dict, List

import django

from meshdb.utils.spreadsheet_import import logger
from meshdb.utils.spreadsheet_import.fetch_osticket_data import import_ticket_numbers_from_osticket

logger.configure()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()

from meshapi import models
from meshdb.utils.spreadsheet_import.building.constants import INVALID_BIN_NUMBERS
from meshdb.utils.spreadsheet_import.building.resolve_address import AddressParser
from meshdb.utils.spreadsheet_import.csv_load import (
    DroppedModification,
    get_spreadsheet_links,
    get_spreadsheet_rows,
    get_spreadsheet_sectors,
    print_dropped_edit_report,
    print_failure_report,
)
from meshdb.utils.spreadsheet_import.parse_building import get_or_create_building
from meshdb.utils.spreadsheet_import.parse_devices import load_access_points, load_devices_supplement_with_uisp
from meshdb.utils.spreadsheet_import.parse_install import create_install, normalize_install_to_primary_building_node
from meshdb.utils.spreadsheet_import.parse_link import load_links_supplement_with_uisp
from meshdb.utils.spreadsheet_import.parse_member import get_or_create_member
from meshdb.utils.spreadsheet_import.parse_node import get_node_type, get_or_create_node, normalize_building_node_links


def main():
    if len(sys.argv) != 4:
        print("Usage: meshdb-spreadsheet-import [Path to Form Responses CSV] [Path to Links CSV] [Path to Sectors CSV]")
        return

    if (
        len(models.Member.objects.all()) != 0
        or len(models.Building.objects.all()) != 0
        or len(models.Node.objects.all()) != 0
        or len(models.Install.objects.all()) != 0
    ):
        logging.error(
            "Expected database to be empty before ingesting from spreadsheet data. "
            "Check that the DB is empty (python src/manage.py flush) and try again"
        )
        sys.exit(1)

    form_responses_path, links_path, sectors_path = sys.argv[1:4]

    rows, reassigned_rows, skipped = get_spreadsheet_rows(form_responses_path)
    logging.info(f'Loaded {len(rows)} rows from "{form_responses_path}"')

    try:
        logging.info(f"Creating {len(reassigned_rows)} nodes for rows marked 'NN Reassigned'...")

        nn_bin_map: Dict[int, int] = {}
        for row in reassigned_rows:
            node = models.Node(
                network_number=row.id,
                name=row.nodeName if row.nodeName else None,
                latitude=row.latitude,
                longitude=row.longitude,
                altitude=row.altitude,
                status=models.Node.NodeStatus.PLANNED,  # This will get overridden later
                type=get_node_type(row.notes, row.nodeName),
                notes=f"Spreadsheet Notes:\n"
                f"{row.notes if row.notes else None}\n\n"
                f"Spreadsheet Notes2:\n"
                f"{row.notes2 if row.notes2 else None}\n\n",
            )
            node.save()
            dob_bin = row.bin if row.bin and row.bin > 0 and row.bin not in INVALID_BIN_NUMBERS else None
            if dob_bin and node.network_number:
                nn_bin_map[node.network_number] = dob_bin

        member_duplicate_counts = defaultdict(lambda: 1)

        addr_parser = AddressParser()

        dropped_modifications: List[DroppedModification] = []

        max_install_num = max(row.id for row in rows)

        start_time = time.time()
        logging.info(f"Processing install # {rows[0].id}/{max_install_num}...")
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

            node = get_or_create_node(row)

            if not node and building.primary_node:
                node = building.primary_node

            node_type_from_row = get_node_type(row.notes, row.nodeName)
            if not node and node_type_from_row in [
                models.Node.NodeType.HUB,
                models.Node.NodeType.SUPERNODE,
                models.Node.NodeType.POP,
            ]:
                node = models.Node(
                    name=row.nodeName if row.nodeName else None,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    altitude=row.altitude,
                    status=models.Node.NodeStatus.PLANNED,
                    type=node_type_from_row,
                    notes=f"Spreadsheet Notes:\n"
                    f"{row.notes if row.notes else None}\n\n"
                    f"Spreadsheet Notes2:\n"
                    f"{row.notes2 if row.notes2 else None}\n\n",
                )

            install = create_install(row)

            install.building = building
            install.member = member
            install.node = node

            node_status_for_current_row = models.Node.NodeStatus.INACTIVE
            if install.status == models.Install.InstallStatus.ACTIVE:
                node_status_for_current_row = models.Node.NodeStatus.ACTIVE
            elif install.status in [
                models.Install.InstallStatus.REQUEST_RECEIVED,
                models.Install.InstallStatus.PENDING,
            ]:
                node_status_for_current_row = models.Node.NodeStatus.PLANNED

            member.save()

            if node:
                if not node.status:
                    # If this is a new node, just use the new status
                    node.status = node_status_for_current_row
                else:
                    # If this node already exists and is ACTIVE, or is active on the current install
                    # mark the node active, since any active install makes a node active
                    # However, if the existing node is not active and the current install is not ACTIVE,
                    # override any potential PLANNED status that was previously set on the node
                    # with INACTIVE since this is probably and abandoned node with an extra install
                    # request hanging off the side.
                    # Otherwise, don't touch the existing status, which allows a node with only
                    # REQUEST_RECEIVED installs to show as PLANNED
                    if (
                        node.status == models.Node.NodeStatus.ACTIVE
                        or node_status_for_current_row == models.Node.NodeStatus.ACTIVE
                    ):
                        node.status = models.Node.NodeStatus.ACTIVE
                    elif node_status_for_current_row == models.Node.NodeStatus.INACTIVE:
                        node.status = models.Node.NodeStatus.INACTIVE

                if node.status == models.Node.NodeStatus.ACTIVE:
                    # If we have any active installs, clear any previously marked abandon date since
                    # this node is still active
                    node.abandon_date = None

                node.save()

            building.save()
            install.save()

            if node:
                # Associate the node and building that we are currently working with
                building.nodes.add(node)

                # Ensure the cluster of nodes and buildings this row is a part of is self-consistent
                normalize_building_node_links(building, node)

        # Do address-based node normalization (i.e. ensure that installs with the same address
        # are associated with the same node when applicable)
        for install in models.Install.objects.all():
            normalize_install_to_primary_building_node(install)

        # Confirm that the appropriate NN -> Building relations have been formed via the Install
        # import that we would expect from the NN only rows
        for nn, _bin in nn_bin_map.items():
            node = models.Node.objects.get(network_number=nn)
            building_match = node.buildings.filter(bin=_bin)
            if not building_match:
                logging.warning(
                    f"Warning, from NN data, expected NN{nn} to be connected to at least one building "
                    f"with DOB number {_bin} but no such connection was found. Adding it now..."
                )
                building_candidates = models.Building.objects.filter(bin=_bin)
                if len(building_candidates) == 0:
                    logging.error(
                        f"Found no buildings with DOB BIN {_bin}, but this BIN is specified in "
                        f"spreadsheet row #{nn}. Is this BIN correct?"
                    )
                    continue
                for building in building_candidates:
                    if not building.primary_node:
                        building.primary_node = node
                        building.save()
                    else:
                        node.buildings.add(building)

        for node in models.Node.objects.all():
            if not node.installs.all():
                # If we don't have any installs associated with this node, it is not
                # active or planned, mark it as INACTIVE
                logging.warning(f"Found node imported without installs (NN{node.network_number}), marking INACTIVE")
                node.status = models.Node.NodeStatus.INACTIVE
                node.save()

        # Create an AP device for each access point install
        load_access_points(rows)

        logging.debug("Top 15 duplicate emails and submission counts:")
        for email, count in sorted(member_duplicate_counts.items(), key=lambda item: item[1], reverse=True)[:15]:
            logging.debug(f"{email}: {count}")

        logging.info(f"Importing devices from UISP & '{sectors_path}'")
        load_devices_supplement_with_uisp(get_spreadsheet_sectors(sectors_path))

        logging.info(f"Importing links from UISP & '{links_path}'")
        load_links_supplement_with_uisp(get_spreadsheet_links((links_path)))

        logging.info(f"Importing ticket numbers from OSTicket")
        import_ticket_numbers_from_osticket()
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


if __name__ == "__main__":
    main()
