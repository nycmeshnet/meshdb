import dataclasses
import datetime
import json
import logging
import os
from dataclasses import dataclass, fields
from typing import Optional

import boto3
from botocore.client import ClientError, Config

from meshapi.views.forms import JoinFormRequest

# Only used for dev with Minio. Don't set in deployed or unit testing envs
JOIN_RECORD_ENDPOINT = os.environ.get("S3_ENDPOINT", None)

JOIN_RECORD_BUCKET_NAME = os.environ.get("JOIN_RECORD_BUCKET_NAME")
JOIN_RECORD_PREFIX = os.environ.get("JOIN_RECORD_PREFIX", "sample-basename")


@dataclass
class JoinRecord(JoinFormRequest):
    version: int
    uuid: str  # XXX (wdn): Should we consider making this a UUID?
    submission_time: str
    code: str
    replayed: int
    install_number: Optional[int]


def s3_content_to_join_record(object_key: str, content: str) -> JoinRecord:
    content_json = json.loads(content)
    mapped_content_json = {key.name: content_json.get(key.name) for key in fields(JoinRecord)}
    join_record = JoinRecord(**mapped_content_json)

    # Convert S3 path to datetime
    # "dev-join-form-submissions/2024/10/28/12/27/00.json"
    datetime_components = object_key.split(".")[0].split("/")[1:]
    year, month, day, hour, minute, second = map(int, datetime_components)
    result_datetime = datetime.datetime(year, month, day, hour, minute, second)
    join_record.submission_time = result_datetime.isoformat()
    return join_record


class JoinRecordProcessor:
    def __init__(self) -> None:
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=JOIN_RECORD_ENDPOINT,
            config=Config(signature_version="s3v4"),  # Ensure S3 signature v4 is used
        )

    def upload(self, join_record: JoinRecord, key: str) -> None:
        try:
            self.s3_client.put_object(
                Bucket=JOIN_RECORD_BUCKET_NAME,
                Key=key,
                Body=json.dumps(dataclasses.asdict(join_record)),
                ContentType="application/json",
            )
        except ClientError as e:
            logging.error(e)

    def get_all(self, since: Optional[datetime.datetime] = None, submission_prefix: str = "post") -> list[JoinRecord]:
        response = self.s3_client.list_objects_v2(
            Bucket=JOIN_RECORD_BUCKET_NAME,
            Prefix=f"{JOIN_RECORD_PREFIX}/{submission_prefix}",
            StartAfter=since.strftime(f"{JOIN_RECORD_PREFIX}/%Y/%m/%d/%H/%M/%S.json")
            if isinstance(since, datetime.datetime)
            else "",
        )

        join_records = []

        # Loop through each object and get its contents
        if "Contents" in response:
            for obj in response["Contents"]:
                object_key = obj["Key"]

                # Get object content
                content_object = self.s3_client.get_object(Bucket=JOIN_RECORD_BUCKET_NAME, Key=object_key)
                content = content_object["Body"].read().decode("utf-8")

                join_records.append(s3_content_to_join_record(object_key, content))
        else:
            print("Bucket is empty or does not exist.")

        return join_records

    # I hardcoded the folder prefix to prevent any shenanigans
    def flush_test_data(self) -> None:
        folder_path = "join-record-test"

        objects_to_delete = self.s3_client.list_objects_v2(Bucket=JOIN_RECORD_BUCKET_NAME, Prefix=folder_path)

        if "Contents" in objects_to_delete:
            delete_keys = [{"Key": obj["Key"]} for obj in objects_to_delete["Contents"]]

            self.s3_client.delete_objects(Bucket=JOIN_RECORD_BUCKET_NAME, Delete={"Objects": delete_keys})
            print(f"Folder '{folder_path}' deleted from bucket '{JOIN_RECORD_BUCKET_NAME}'.")
        else:
            print(f"No objects found in folder '{folder_path}'.")

    def ensure_pre_post_consistency(self, since: datetime.datetime):
        # Get join records from both pre and post submissions so we can make sure
        # there are no discrepancies
        # Convert the lists to dictionaries to make them easier to search by UUID
        pre_join_records_dict = {}
        for record in self.get_all(since, "pre"):
            if record.version >= 2:
                pre_join_records_dict[record.uuid] = record

        post_join_records_dict = {}
        for record in self.get_all(since, "pre"):
            if record.version >= 2:
                post_join_records_dict[record.uuid] = record

        replayed_join_records_dict = {}
        for record in self.get_all(since, "pre"):
            if record.version >= 2:
                replayed_join_records_dict[record.uuid] = record

        for uuid, record in pre_join_records_dict.values():
            if post_join_records_dict.get(uuid):
                continue
            key = self.get_key(record)
            logging.warning(
                f"Did not find a corresponding post-submission join record for pre-submission join record {key}. Will supplement post-submission records."
            )
            post_join_records_dict[uuid] = record

        # Remove join records that have already been successfully replayed
        for uuid, record in replayed_join_records_dict.values():
            if post_join_records_dict.get(uuid):
               post_join_records_dict.pop(uuid) 

        return post_join_records_dict


    @staticmethod
    def get_key(join_record: JoinRecord, pre: bool = False):
        submission_time = datetime.datetime.fromisoformat(join_record.submission_time)
        return submission_time.strftime(
            f"{JOIN_RECORD_PREFIX}/{"pre" if pre else "post"}/{join_record.uuid.split(" - ")[1]}/%Y/%m/%d/%H/%M/%S.json"
        )
