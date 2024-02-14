import logging
from typing import Optional

from django.db.models import Q

from meshapi import models
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetLink, SpreadsheetLinkStatus


def create_link(spreadsheet_link: SpreadsheetLink) -> Optional[models.Link]:
    try:
        from_building = models.Building.objects.filter(
            Q(installs__install_number=spreadsheet_link.from_install_num)
            | Q(installs__network_number=spreadsheet_link.from_install_num)
            | Q(primary_nn=spreadsheet_link.from_install_num),
        )[0]
        to_building = models.Building.objects.filter(
            Q(installs__install_number=spreadsheet_link.to_install_num)
            | Q(installs__network_number=spreadsheet_link.to_install_num)
            | Q(primary_nn=spreadsheet_link.to_install_num),
        )[0]
    except IndexError:
        message = (
            f"Could not find building for install {spreadsheet_link.from_install_num} or "
            f"{spreadsheet_link.to_install_num}"
        )
        if spreadsheet_link.status != SpreadsheetLinkStatus.dead:
            raise ValueError(message)
        else:
            logging.warning(message + ". But this link is dead, skipping this spreadsheet row")
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
        from_building=from_building,
        to_building=to_building,
        status=status,
        type=link_type,
        install_date=spreadsheet_link.install_date,
        abandon_date=spreadsheet_link.abandon_date,
        description=spreadsheet_link.where_to_where if spreadsheet_link.where_to_where else None,
        notes=link_notes if link_notes else None,
    )
    return link
