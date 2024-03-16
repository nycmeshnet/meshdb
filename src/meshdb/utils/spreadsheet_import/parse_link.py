import logging
import os
from typing import List, Optional

import django
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()


from meshapi import models
from meshapi.models import Device, Install, Link, Node
from meshdb.utils.spreadsheet_import.building.lookup import get_building_from_node_id
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetLink, SpreadsheetLinkStatus, get_spreadsheet_links
from meshdb.utils.spreadsheet_import.fetch_uisp import download_uisp_devices, download_uisp_links


def convert_spreadsheet_link_type(status: SpreadsheetLinkStatus) -> Link.LinkType:
    link_type = None
    if status in [
        SpreadsheetLinkStatus.active,
    ]:
        link_type = models.Link.LinkType.STANDARD
    elif status == SpreadsheetLinkStatus.vpn:
        link_type = models.Link.LinkType.VPN
    elif status == SpreadsheetLinkStatus.sixty_ghz:
        link_type = models.Link.LinkType.MMWAVE
    elif status == SpreadsheetLinkStatus.fiber:
        link_type = models.Link.LinkType.FIBER

    return link_type


def convert_spreadsheet_link_status(status: SpreadsheetLinkStatus) -> Link.LinkStatus:
    if status in [
        SpreadsheetLinkStatus.vpn,
        SpreadsheetLinkStatus.active,
        SpreadsheetLinkStatus.sixty_ghz,
        SpreadsheetLinkStatus.fiber,
    ]:
        return models.Link.LinkStatus.ACTIVE
    elif status == SpreadsheetLinkStatus.dead:
        return models.Link.LinkStatus.INACTIVE
    elif status == SpreadsheetLinkStatus.planned:
        return models.Link.LinkStatus.PLANNED
    else:
        raise ValueError(f"Invalid spreadsheet link status {status}")


def get_node_from_spreadsheet_id(spreadsheet_node_id: int) -> Node:
    try:
        return Node.objects.get(network_number=spreadsheet_node_id)
    except Node.DoesNotExist:
        return Install.objects.get(install_number=spreadsheet_node_id).node


def get_representative_device_for_node(node: Node) -> Device:
    if node is None:
        raise ValueError("Node must exist!")

    search_terms = ["core", "omni"]

    # Look for a core router, and use that if available, if not, look for an omni
    for search_term in search_terms:
        candidates = node.devices.filter(name__icontains=search_term)
        if len(candidates):
            return candidates.first()

    # Otherwise return an arbitrary device
    return node.devices.first()


def create_link(spreadsheet_link: SpreadsheetLink) -> Optional[models.Link]:
    try:
        from_device = get_representative_device_for_node(get_node_from_spreadsheet_id(spreadsheet_link.from_node_id))
        to_device = get_representative_device_for_node(get_node_from_spreadsheet_id(spreadsheet_link.to_node_id))
    except ValueError as e:
        if spreadsheet_link.status != SpreadsheetLinkStatus.dead:
            logging.error(
                f"Could not create link from {spreadsheet_link.from_node_id} to {spreadsheet_link.to_node_id}. "
                f"Can't find one or more nodes"
            )
            # raise e
        else:
            logging.debug(
                f"Could not create link from {spreadsheet_link.from_node_id} to {spreadsheet_link.to_node_id}."
                f" But this link is dead, skipping this spreadsheet row"
            )
        return None

    if not from_device or not to_device:
        return None

    link_notes = "\n".join([spreadsheet_link.notes, spreadsheet_link.comments]).strip()
    link = models.Link(
        from_device=from_device,
        to_device=to_device,
        status=convert_spreadsheet_link_status(spreadsheet_link.status),
        type=convert_spreadsheet_link_type(spreadsheet_link.status),
        install_date=spreadsheet_link.install_date,
        abandon_date=spreadsheet_link.abandon_date,
        description=spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None,
        notes=link_notes if link_notes else None,
        uisp_id=None,
    )
    return link


def load_links_supplement_with_uisp(spreadsheet_links: List[SpreadsheetLink]):
    uisp_links = download_uisp_links()

    for uisp_link in uisp_links:
        try:
            if not uisp_link["from"]["device"]:
                continue

            from_device = Device.objects.get(uisp_id=uisp_link["from"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            if uisp_link["from"]["device"]["identification"]["category"] != "optical":
                logging.warning(
                    f"Skipping UISP link because device "
                    f"{uisp_link['from']['device']['identification']['name']} could not be found"
                )
            continue

        try:
            if not uisp_link["to"]["device"]:
                continue

            to_device = Device.objects.get(uisp_id=uisp_link["to"]["device"]["identification"]["id"])
        except Device.DoesNotExist:
            if uisp_link["to"]["device"]["identification"]["category"] != "optical":
                logging.warning(
                    f"Skipping UISP link because device "
                    f"{uisp_link['to']['device']['identification']['name']} could not be found"
                )
            continue

        if len(
            Link.objects.filter(
                Q(from_device=from_device, to_device=to_device) | Q(from_device=to_device, to_device=from_device)
            )
        ):
            logging.debug(f"Skipping duplicate link between {from_device} and {to_device}")
            continue

        if uisp_link["state"] == "active":
            status = Link.LinkStatus.ACTIVE
        else:
            status = Link.LinkStatus.INACTIVE

        if uisp_link["type"] == "wireless":
            if uisp_link["frequency"] and uisp_link["frequency"] > 8_000:
                type = Link.LinkType.MMWAVE
            else:
                type = Link.LinkType.STANDARD
        elif uisp_link["type"] == "ethernet":
            type = Link.LinkType.STANDARD
        elif uisp_link["type"] == "pon":
            type = Link.LinkType.FIBER
        else:
            raise ValueError(f"Unexpected UISP link type: {uisp_link['type']} for link {uisp_link['id']}")

        link = Link(
            from_device=from_device,
            to_device=to_device,
            status=status,
            type=type,
            uisp_id=uisp_link["id"],
            # UISP doesn't track the following info, but we can maybe fill it in below from spreadsheet data
            install_date=None,
            abandon_date=None,
            description=None,
            notes=None,
        )
        link.save()

    for spreadsheet_link in spreadsheet_links:
        try:
            # TODO: this method of node lookup doesn't work for campus links like the vernon APs
            # TODO: this doesn't work for "potential" links between potential installs
            from_node = get_node_from_spreadsheet_id(spreadsheet_link.from_node_id)
            to_node = get_node_from_spreadsheet_id(spreadsheet_link.to_node_id)
        except ObjectDoesNotExist:
            logging.warning(
                f"Skipping link {spreadsheet_link.from_node_id} to {spreadsheet_link.to_node_id}. "
                f"Can't find one or more nodes"
            )
            continue

        existing_links = Link.objects.filter(
            Q(from_device__node=from_node, to_device__node=to_node)
            | Q(to_device__node=from_node, from_device__node=to_node)
        )

        link_notes = "\n".join([spreadsheet_link.notes, spreadsheet_link.comments]).strip()

        if len(existing_links):
            if len(existing_links) > 1:
                logging.info(
                    f"Duplicate links detected between {from_node} and {to_node}, "
                    f"annotating all of them with the same spreadsheet metadata"
                )
            for link in existing_links:
                link.status = convert_spreadsheet_link_status(spreadsheet_link.status)
                link.install_date = spreadsheet_link.install_date
                if link.type == Link.LinkType.STANDARD:
                    # If UISP indicates a special type of link, keep that.
                    # Otherwise, defer to the spreadsheet
                    link.type = convert_spreadsheet_link_type(spreadsheet_link.status) or Link.LinkType.STANDARD
                link.abandon_date = spreadsheet_link.abandon_date
                link.description = spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None
                link.notes = link_notes if link_notes else None
                link.save()
        else:
            # If we don't have any possible existing links to annotate, make a brand new one
            link = create_link(spreadsheet_link)
            if link:
                link.save()


if __name__ == "__main__":
    links_path = "spreadsheet_data/New Node Form (Responses) - Links.csv"
    load_links_supplement_with_uisp(get_spreadsheet_links((links_path)))
