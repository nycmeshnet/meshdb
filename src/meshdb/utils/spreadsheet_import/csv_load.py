import csv
import dataclasses
import datetime
import logging
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SpreadsheetStatus(Enum):
    installed = "Installed"
    nnAssigned = "NN assigned"
    toBeScheduled = "To be scheduled"
    scheduled = "Scheduled"
    interested = "Interested"
    poweredOff = "Powered Off"
    abandoned = "Abandoned"
    invalid = "Invalid"
    dupe = "Dupe"
    noLos = "No LoS"
    notInterested = "Not Interested"
    noReply = "No Reply"
    unsubscribe = "Unsubscribe"
    notContactedYet = "Not Contacted Yet"
    noStatus = ""


@dataclasses.dataclass
class SpreadsheetRow:
    request_date: datetime.datetime
    address: str
    neighborhood: Optional[str]
    apartment: Optional[str]
    name: Optional[str]
    email: str
    secondEmail: str
    stripeEmail: str
    phone: Optional[str]
    roofAccess: bool
    status: SpreadsheetStatus
    installDate: Optional[datetime.date]
    abandonDate: Optional[datetime.date]
    nodeName: Optional[str]
    notes: Optional[str]
    notes2: Optional[str]
    installNotes: Optional[str]
    contactNotes: Optional[str]
    referral: Optional[str]
    id: int
    nn: Optional[int]
    bin: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]


@dataclasses.dataclass
class DroppedModification:
    original_row_ids: List[int]
    new_row_id: int
    deduplication_value: str
    modified_property: str
    database_value: str
    dropped_value: str


def get_spreadsheet_rows(
    form_responses_path: str,
) -> Tuple[List[SpreadsheetRow], Dict[int, str]]:
    with open(form_responses_path, "r") as input_file:
        csv_reader = csv.DictReader(input_file)

        skipped_rows: Dict[int, str] = {}
        nodes: List[SpreadsheetRow] = []

        for i, row in enumerate(csv_reader):
            # Last row is placeholder
            try:
                node_id = int(row["ID"])
            except ValueError:
                skipped_rows[i + 2] = "Invalid ID"
                continue

            try:
                request_date = datetime.datetime.strptime(row["Timestamp"], "%m/%d/%Y %H:%M:%S")
            except ValueError:
                skipped_rows[node_id] = "Invalid timestamp"
                continue

            try:
                install_date = datetime.datetime.strptime(row["installDate"], "%m/%d/%Y")
            except ValueError:
                install_date = None

            try:
                abandon_date = datetime.datetime.strptime(row["abandonDate"], "%m/%d/%Y")
            except ValueError:
                abandon_date = None

            re_assigned_as_nn = False
            try:
                nn = row["NN"].lower().strip()
                re_assigned_as_nn = nn.startswith("x-")
                nn = int(nn) if nn is not None and nn != "" and not re_assigned_as_nn else None
            except (KeyError, ValueError):
                nn = None

            node = SpreadsheetRow(
                request_date=request_date,
                address=row["Location"],
                neighborhood=row["Neighborhood"] if row["Neighborhood"] else None,
                apartment=row["Apartment number"],
                name=row["Name"],
                email=row["Email"].lower().strip(),
                stripeEmail=row["Stripe Email"].lower().strip(),
                secondEmail=row["2nd profile email"].lower().strip(),
                phone=row["Phone"],
                roofAccess=row["Rooftop Access"] == "I have Rooftop access",
                status=SpreadsheetStatus(row["Status"].replace("dupe", "Dupe")),
                installDate=install_date,
                abandonDate=abandon_date,
                nodeName=row["nodeName"],
                notes=row["notes"],
                notes2=row["notes2"],
                installNotes=row["install notes"],
                contactNotes=row["contact notes"],
                referral=row["Referral"],
                id=node_id,
                nn=nn,
                bin=int(row["BIN"]) if row["BIN"] is not None and row["BIN"] != "" else None,
                latitude=float(row["Latitude"]) if row["Latitude"] is not None and row["Latitude"] != "" else None,
                longitude=float(row["Longitude"]) if row["Longitude"] is not None and row["Longitude"] != "" else None,
                altitude=float(row["Altitude"]) if row["Altitude"] is not None and row["Altitude"] != "" else None,
            )

            if not node.latitude or not node.longitude:
                skipped_rows[node_id] = "Missing lat or lon - Google couldn't parse addr?"
                continue

            if re_assigned_as_nn:
                skipped_rows[node_id] = "Reassigned as NN for another row"
                continue

            nodes.append(node)

        return nodes, skipped_rows


def print_failure_report(skipped_rows: Dict[int, str], original_input_file: str, fname_overide: str = None) -> None:
    fname = fname_overide if fname_overide else "skipped_rows.csv"
    if len(skipped_rows) > 0:
        logging.warning(
            f'Skipped {len(skipped_rows)} rows from input CSV file "{original_input_file}". '
            f'See "{fname}" for more info'
        )

    with open(fname, "w") as f:
        with open(original_input_file, "r") as input_file:
            csv_reader = csv.DictReader(input_file)

            csv_writer = csv.DictWriter(f, ["RejectionReason"] + list(csv_reader.fieldnames))
            csv_writer.writeheader()

            for i, row in enumerate(csv_reader):
                if i + 2 in skipped_rows:
                    row["RejectionReason"] = skipped_rows[i + 2]
                    csv_writer.writerow(row)


def print_dropped_edit_report(
    dropped_edits: List[DroppedModification], original_input_file: str, fname_overide: str = None
) -> None:
    fname = fname_overide if fname_overide else "dropped_edits.csv"
    if len(dropped_edits) > 0:
        logging.warning(
            f"Skipped {len(dropped_edits)} edits to previously established values while parsing"
            f' input CSV file "{original_input_file}". '
            f'See "{fname}" for more info'
        )

    dropped_edits_dict = defaultdict(lambda: [])
    for edit in dropped_edits:
        dropped_edits_dict[edit.new_row_id].append(edit)

    with open(fname, "w") as f:
        with open(original_input_file, "r") as input_file:
            csv_reader = csv.DictReader(input_file)

            csv_writer = csv.DictWriter(
                f,
                [
                    "OriginalRowID(s)",
                    "DroppedRowID",
                    "DeduplicationValue",
                    "ModifiedProperty",
                    "DatabaseValue",
                    "DroppedValue",
                ]
                # + list(csv_reader.fieldnames),
            )
            csv_writer.writeheader()

            for i, row in enumerate(csv_reader):
                if i + 2 in dropped_edits_dict:
                    for edit in dropped_edits_dict[i + 2]:
                        new_fields = {}
                        new_fields["OriginalRowID(s)"] = ", ".join(str(row_id) for row_id in edit.original_row_ids)
                        new_fields["DroppedRowID"] = edit.new_row_id
                        new_fields["DeduplicationValue"] = edit.deduplication_value
                        new_fields["ModifiedProperty"] = edit.modified_property
                        new_fields["DatabaseValue"] = edit.database_value
                        new_fields["DroppedValue"] = edit.dropped_value
                        csv_writer.writerow(
                            {
                                **new_fields,
                                # **row,
                            }
                        )
