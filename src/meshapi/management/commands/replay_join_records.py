import logging
from argparse import ArgumentParser
from dataclasses import asdict, fields
from datetime import datetime, timedelta, timezone
from typing import Any

from django.core.management.base import BaseCommand
from prettytable import PrettyTable

from meshapi.util.join_records import JoinRecord, JoinRecordProcessor, SubmissionStage
from meshapi.views.forms import JoinFormRequest, process_join_form


class Command(BaseCommand):
    help = "Replay join form submissions that we may not have accepted properly."
    "Defaults to viewing. Pass --write to write the records to MeshDB."
    hidden_fields = ["version", "uuid", "replayed"]

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
            help="Show records submitted since this date and time (UTC, 24-Hour) (yyyy-mm-ddTHH:MM:SS)",
        )

        parser.add_argument(
            "--all-columns",
            action="store_true",
            help=f"Display all information from the Join Record: {self.hidden_fields}",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        logging.info("Fetching Join Records...")

        p = JoinRecordProcessor()

        # Default to getting join records from 1 week ago unless otherwise specified
        since = options["since"] or self.past_week()

        # Ensure that the join records in pre-submission match the ones in post-submission
        # This method will get both sets of records and supplement the post-submission
        # records if any are missing.
        consistent_join_records_dict = p.ensure_pre_post_consistency(since)

        table = PrettyTable()
        table.padding_width = 0

        # These fields aren't really that relevant to human eyes.
        if options["all_columns"]:
            hidden_fields = []
        else:
            hidden_fields = self.hidden_fields
        table.field_names = (key.name for key in fields(JoinRecord) if key.name not in hidden_fields)

        join_records_to_replay = {}

        for uuid, record in consistent_join_records_dict.items():
            if not options["all"]:
                # Ignore submissions that are known good
                if record.install_number:
                    continue

                # Don't bother replaying 400's. All we care about are 500's and nulls
                if record.code and 400 <= int(record.code) and int(record.code) <= 499:
                    continue

            join_records_to_replay[uuid] = record
            record_as_dict = asdict(record)
            for k in hidden_fields:
                record_as_dict.pop(k)
            table.add_row(record_as_dict.values())

        if not options["all"]:
            print("The following Join Requests HAVE NOT been successfully submitted.")

        print(table)

        if not options["write"]:
            return

        if not join_records_to_replay:
            logging.warning("Found no join records to replay. Quitting")
            return

        if not options["noinput"]:
            proceed_with_replay = input("Proceed with replay? (y/N): ")
            if proceed_with_replay.lower() not in ["yes", "y"]:
                print("Operation cancelled.")
                return

        print("Replaying Join Records...")

        for record in join_records_to_replay.values():
            # Make the request
            r = JoinFormRequest(
                **{k: v for k, v in record.__dict__.items() if k in JoinFormRequest.__dataclass_fields__}
            )
            response = process_join_form(r)

            print(f"{response.status_code} : {response.data}")

            if response.status_code == 409:
                print("Please confirm some information:")
                print("Changed Info:")

                confirmation_table = PrettyTable()
                confirmation_table.padding_width = 0
                confirmation_table.field_names = ["Field", "Original", "Suggested"]

                for field, value in response.data["changed_info"].items():
                    original_value = r.__dict__[field]
                    confirmation_table.add_row([field, original_value, value])

                print(confirmation_table)

                if not options["noinput"]:
                    # Trap the user until they make a valid choice
                    while True:
                        user_input = input("(A)ccept/(R)eject/(S)kip ?: ")
                        if user_input in ["accept", "reject", "skip", "a", "r", "s"]:
                            break
                else:
                    user_input = "accept"
                    logging.warning("--no-input was specified, so auto-accepting")

                if user_input.lower() in ["accept", "a"]:
                    print("Re-submitting with accepted changes...")
                    r.__dict__.update(response.data["changed_info"])

                    # If this doesn't work, then uh, skill issue.
                    response = process_join_form(r)
                    logging.info(f"Code: {response.status_code}")

                elif user_input.lower() in ["reject", "r"]:
                    print("Rejecting changes and re-submitting...")
                    r.__dict__.update({"trust_me_bro": True})

                    # If this doesn't work, then uh, skill issue.
                    response = process_join_form(r)
                    logging.info(f"Code: {response.status_code}")

                elif user_input.lower() in ["skip", "s"]:
                    print("Skipping...")
                    continue

            record.code = str(response.status_code)
            record.replayed += 1
            if response.data.get("install_number"):
                record.install_number = response.data["install_number"]
            else:
                logging.error(
                    "Replay unsuccessful! Did not get an install number for "
                    f"record: {JoinRecordProcessor.get_key(record, SubmissionStage.POST)}."
                )

            key = JoinRecordProcessor.get_key(record, SubmissionStage.POST)
            p.upload(record, key)

    @staticmethod
    def past_week() -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=7)
