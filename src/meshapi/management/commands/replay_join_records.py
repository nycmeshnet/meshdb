from argparse import ArgumentParser
from dataclasses import asdict, fields
import json
import logging
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

        parser.add_argument("--json", action="store_true", help="Print records as JSON instead of in a table.")

    def handle(self, *args: Any, **options: Any) -> None:
        p = JoinRecordProcessor()

        join_records = p.get_all()
                
        table = PrettyTable()
        table.padding_width = 0

        table.field_names = (key.name for key in fields(JoinRecord))

        for entry in join_records:
            # Ignore submissions that are known good
            if (not options["all"]) and (entry.code == "200" or entry.code == "201"):
                join_records.remove(entry)
                continue

            table.add_row(asdict(entry).values())
        
        if not options["all"]:
            print("The following Join Requests have not been successfully submitted.")

        if options["json"]:
            for record in join_records:
                d = asdict(record)
                d['submission_time'] = d['submission_time'].strftime("%Y-%m-%d %H:%M:%S")  # Custom format
                print(json.dumps(d))
        else:
            print(table)

        if options["look"]:
            return

        if not options["noinput"]:
            proceed_with_replay = input("Proceed with replay? (y/N): ")
            if proceed_with_replay.lower() != "yes" and proceed_with_replay.lower() != "y":
                logging.warning("Operation cancelled.")

        logging.info("Replaying Join Records...")

        for record in join_records:
            # Make the request
            r = JoinFormRequest(**record)
            response = process_join_form(r)
            record.replays += 1
            record.replay_code = response.status_code

            # Update info to S3
            key = record.submission_time.strftime(f"{JOIN_RECORD_BASE_NAME}/%Y/%m/%d/%H/%M/%S.json") 
            p.upload(record, key)
            
