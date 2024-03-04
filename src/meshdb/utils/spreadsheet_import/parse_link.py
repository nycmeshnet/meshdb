import logging
from typing import Optional

from meshapi import models
from meshdb.utils.spreadsheet_import.building.lookup import get_building_from_node_id
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetLink, SpreadsheetLinkStatus


def create_link(spreadsheet_link: SpreadsheetLink) -> Optional[models.Link]:
    try:
        from_device = get_building_from_node_id(spreadsheet_link.from_node_id)
        to_device = get_building_from_node_id(spreadsheet_link.to_node_id)
    except ValueError as e:
        if spreadsheet_link.status != SpreadsheetLinkStatus.dead:
            raise e
        else:
            logging.warning(f"Error while parsing links: { e }. But this link is dead, skipping this spreadsheet row")
            return None

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
    elif spreadsheet_link.status == SpreadsheetLinkStatus.fiber:
        link_type = models.Link.LinkType.FIBER

    link_notes = "\n".join([spreadsheet_link.notes, spreadsheet_link.comments]).strip()
    link = models.Link(
        from_device=from_device,
        to_device=to_device,
        status=status,
        type=link_type,
        install_date=spreadsheet_link.install_date,
        abandon_date=spreadsheet_link.abandon_date,
        description=spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None,
        notes=link_notes if link_notes else None,
    )
    return link
