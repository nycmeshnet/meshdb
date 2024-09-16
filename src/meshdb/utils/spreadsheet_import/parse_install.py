import logging
from typing import Optional

from meshapi import models
from meshdb.utils.spreadsheet_import.csv_load import SpreadsheetRow, SpreadsheetStatus


def translate_spreadsheet_status_to_db_status(
    status: SpreadsheetStatus,
) -> models.Install.InstallStatus:
    if status in {SpreadsheetStatus.noStatus}:
        return models.Install.InstallStatus.REQUEST_RECEIVED
    elif status in {
        SpreadsheetStatus.interested,
        SpreadsheetStatus.toBeScheduled,
        SpreadsheetStatus.notContactedYet,
        SpreadsheetStatus.scheduled,
    }:
        return models.Install.InstallStatus.PENDING
    elif status in {SpreadsheetStatus.noLos}:
        return models.Install.InstallStatus.BLOCKED
    elif status in {SpreadsheetStatus.installed}:
        return models.Install.InstallStatus.ACTIVE
    elif status in {
        SpreadsheetStatus.poweredOff,
    }:
        return models.Install.InstallStatus.INACTIVE
    elif status in {SpreadsheetStatus.nnAssigned}:
        return models.Install.InstallStatus.NN_REASSIGNED
    elif status in {
        SpreadsheetStatus.abandoned,
        SpreadsheetStatus.notInterested,
        SpreadsheetStatus.unsubscribe,
        SpreadsheetStatus.invalid,
        SpreadsheetStatus.noReply,
        SpreadsheetStatus.dupe,
    }:
        return models.Install.InstallStatus.CLOSED

    raise ValueError(f"Invalid spreadsheet status: {status} do you need to add another case to this function?")


def create_install(row: SpreadsheetRow) -> Optional[models.Install]:
    install = models.Install(
        install_number=row.id,
        status=translate_spreadsheet_status_to_db_status(row.status),
        ticket_number=None,
        request_date=row.request_date.date(),
        install_date=row.installDate,
        abandon_date=row.abandonDate,
        unit=row.apartment,
        roof_access=row.roofAccess,
        referral=row.referral if row.referral else None,
        notes=f"Spreadsheet Notes:\n"
        f"{row.notes if row.notes else None}\n\n"
        f"Spreadsheet Notes2:\n"
        f"{row.notes2 if row.notes2 else None}\n\n"
        f"Spreadsheet Install Notes:\n"
        f"{row.installNotes if row.installNotes else None}\n\n"
        f"Spreadsheet Contact Notes:\n"
        f"{row.contactNotes if row.contactNotes else None}\n\n"
        f"-------\n",
    )
    if install.status in [
        models.Install.InstallStatus.ACTIVE,
        models.Install.InstallStatus.INACTIVE,
    ]:
        install.diy = "diy" in install.notes.lower()

    return install


def normalize_install_to_primary_building_node(install: models.Install):
    if install.building.primary_node:
        if not install.node:
            install.node = install.building.primary_node
            install.save()
        else:
            if install.node != install.building.primary_node:
                logging.info(f"Mismatch between building.primary_node and node for Install #{install.install_number}")
