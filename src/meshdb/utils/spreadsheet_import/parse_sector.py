import logging
from typing import Optional

from django.db.models import Q

from meshapi import models
from meshdb.utils.spreadsheet_import.building.lookup import get_building_from_node_id
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetSector, SpreadsheetSectorStatus


def create_sector(spreadsheet_sector: SpreadsheetSector) -> Optional[models.Sector]:
    try:
        building = get_building_from_node_id(spreadsheet_sector.node_id)
    except ValueError as e:
        if spreadsheet_sector.status != SpreadsheetSectorStatus.abandoned:
            raise e
        else:
            logging.warning(
                f"Error while parsing sectors: {e}. But this sector is abandoned, skipping this spreadsheet row"
            )
            return None

    if spreadsheet_sector.status == SpreadsheetSectorStatus.active:
        status = models.Sector.SectorStatus.ACTIVE
    elif spreadsheet_sector.status == SpreadsheetSectorStatus.abandoned:
        status = models.Sector.SectorStatus.ABANDONED
    elif spreadsheet_sector.status == SpreadsheetSectorStatus.potential:
        status = models.Sector.SectorStatus.POTENTIAL
    else:
        raise ValueError(f"Invalid spreadsheet sector status {spreadsheet_sector.status}")

    sector_notes = "\n".join([spreadsheet_sector.notes, spreadsheet_sector.comments]).strip()
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
        ssid=spreadsheet_sector.ssid if spreadsheet_sector.ssid else None,
        notes=sector_notes if sector_notes else None,
    )
    return sector
