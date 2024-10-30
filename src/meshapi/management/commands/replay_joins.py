from argparse import ArgumentParser
from dataclasses import asdict, dataclass, fields
import datetime
import json
import logging
import os
from typing import Any

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

import boto3
from botocore.client import Config

from meshapi.views.forms import JoinFormRequest

from prettytable import PLAIN_COLUMNS, PrettyTable

JOIN_RECORD_ENDPOINT   = os.environ.get("JOIN_RECORD_ENDPOINT")
JOIN_RECORD_BUCKET_NAME= os.environ.get("JOIN_RECORD_BUCKET_NAME")
JOIN_RECORD_BASE_NAME  = os.environ.get("JOIN_RECORD_BASE_NAME")
JOIN_RECORD_ACCESS_KEY = os.environ.get("JOIN_RECORD_ACCESS_KEY")
JOIN_RECORD_SECRET_KEY = os.environ.get("JOIN_RECORD_SECRET_KEY")

@dataclass
class JoinRecord(JoinFormRequest):
    submission_time: datetime.datetime
    code: str
    replayed: int
    replay_code: str


class Command(BaseCommand):
    help = "Replay join form submissions that we may not have accepted properly"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        #JOIN_RECORD_ENDPOINT="http://127.0.0.1:9000"
        #JOIN_RECORD_BUCKET_NAME="meshdb-join-form-log"
        #JOIN_RECORD_BASE_NAME="dev-join-form-submissions"
        #JOIN_RECORD_ACCESS_KEY="cuSrLJXKoJYnp1t4VVNR"
        #JOIN_RECORD_SECRET_KEY="Smt5NSfGbaxow4dycCaB1Ne9IPMct8KHyQBs99v6"

                
        s3_client = boto3.client(
            "s3",
            endpoint_url=JOIN_RECORD_ENDPOINT,
            aws_access_key_id=JOIN_RECORD_ACCESS_KEY,
            aws_secret_access_key=JOIN_RECORD_SECRET_KEY,
            config=Config(signature_version="s3v4")  # Ensure S3 signature v4 is used
        )

        response = s3_client.list_objects_v2(Bucket=JOIN_RECORD_BUCKET_NAME)

        join_records = []

        # Loop through each object and get its contents
        if 'Contents' in response:
            for obj in response['Contents']:
                object_key = obj['Key']
                
                # Get object content
                content_object = s3_client.get_object(Bucket=JOIN_RECORD_BUCKET_NAME, Key=object_key)
                content = content_object['Body'].read().decode('utf-8')
                content_json = json.loads(content)
                mapped_content_json = {key.name: content_json.get(key.name) for key in fields(JoinRecord)}
                join_record = JoinRecord(**mapped_content_json)

                # Convert S3 path to datetime
                #"dev-join-form-submissions/2024/10/28/12/27/00.json"
                datetime_components = object_key.split('.')[0].split('/')[1:]
                year, month, day, hour, minute, second = map(int, datetime_components)
                result_datetime = datetime.datetime(year, month, day, hour, minute, second)
                join_record.submission_time = result_datetime


                join_records.append(join_record)
        else:
            print("Bucket is empty or does not exist.")

        
        table = PrettyTable()
        table.padding_width = 0

        table.field_names = (key.name for key in fields(JoinRecord))

        for entry in join_records:
            # Ignore submissions that are known good
            if entry.code == "200" and entry.code == "201":
                continue

            table.add_row(asdict(entry).values())
            
        print("The following Join Requests have not been successfully submitted.")
        print(table)

        return

        proceed_with_replay = input("Proceed with replay? (y/N):")
        if proceed_with_replay.lower() != "yes" and proceed_with_replay.lower() != "y":
            logging.warning("Operation cancelled.")

