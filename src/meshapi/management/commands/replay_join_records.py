from argparse import ArgumentParser
from dataclasses import asdict, fields
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand
from prettytable import PrettyTable

from meshapi.util.join_records import JOIN_RECORD_BASE_NAME, JoinRecord, JoinRecordProcessor
from meshapi.views.forms import JoinFormRequest, process_join_form


class Command(BaseCommand):
    help = "Replay join form submissions that we may not have accepted properly"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--noinput", action="store_true", help="Tells Django to NOT prompt the user for input of any kind."
        )

        parser.add_argument("--all", action="store_true", help="Fetch all Join Records, not just failed ones")

        parser.add_argument("--look", action="store_true", help="Print Join Records and quit")

    def handle(self, *args: Any, **options: Any) -> None:
        p = JoinRecordProcessor()

        join_records = p.get_all()

        table = PrettyTable()
        table.padding_width = 0

        table.field_names = (key.name for key in fields(JoinRecord))

        for entry in join_records:
            if (not options["all"]) and entry.install_number:
                # Ignore submissions that are known good
                join_records.remove(entry)
                continue

            table.add_row(asdict(entry).values())

        if not options["all"]:
            print("The following Join Requests HAVE NOT been successfully submitted.")

        print(table)

        if options["look"]:
            return

        if not options["noinput"]:
            proceed_with_replay = input("Proceed with replay? (y/N): ")
            if proceed_with_replay.lower() != "yes" and proceed_with_replay.lower() != "y":
                print("Operation cancelled.")
                return

        print("Replaying Join Records...")

        for record in join_records:
            # Make the request
            r = JoinFormRequest(
                **{k: v for k, v in record.__dict__.items() if k in JoinFormRequest.__dataclass_fields__}
            )
            response = process_join_form(r)
            record.code = str(response.status_code)
            record.replayed += 1
            if response.data.get("install_number"):
                record.install_number = response.data["install_number"]

            print(f"{response.status_code} : {response.data}")

            # Upload info to S3
            submission_datetime = datetime.fromisoformat(record.submission_time)
            key = submission_datetime.strftime(f"{JOIN_RECORD_BASE_NAME}/%Y/%m/%d/%H/%M/%S.json")
            p.upload(record, key)
