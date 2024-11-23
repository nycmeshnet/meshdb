from argparse import ArgumentParser
from dataclasses import asdict, fields
from datetime import datetime, timedelta, timezone
from typing import Any

from django.core.management.base import BaseCommand
from prettytable import PrettyTable

from meshapi.util.join_records import JOIN_RECORD_PREFIX, JoinRecord, JoinRecordProcessor
from meshapi.views.forms import JoinFormRequest, process_join_form


class Command(BaseCommand):
    help = "Replay join form submissions that we may not have accepted properly."
    "Defaults to viewing. Pass --write to write the records to MeshDB."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--noinput", action="store_true", help="Tells Django to NOT prompt the user for input of any kind."
        )

        parser.add_argument("--all", action="store_true", help="Fetch all Join Records, not just failed ones")

        parser.add_argument(
            "--write",
            action="store_true",
            help="After a confirmation dialogue, replay the records into the Join Form endpoint.",
        )

        parser.add_argument(
            "--since",
            type=lambda s: datetime.fromisoformat(s + "Z"),  # Adding the Z makes this a tz-aware datetime
            help="Show records submitted since this date and time (UTC, 24-Hour) (%Y-%m-%d %H:%M:%S)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        p = JoinRecordProcessor()

        # Default to getting join records from 1 week ago unless otherwise specified
        since = options["since"] or self.past_week()

        join_records = p.get_all(since)

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

        if not options["write"]:
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
            key = submission_datetime.strftime(f"{JOIN_RECORD_PREFIX}/%Y/%m/%d/%H/%M/%S.json")
            p.upload(record, key)

    @staticmethod
    def past_week() -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=7)
