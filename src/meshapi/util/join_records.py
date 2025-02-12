import dataclasses
import datetime
import json
import logging
import os
from dataclasses import dataclass, fields
from enum import Enum
from typing import Optional

import boto3
from botocore.client import ClientError, Config

from meshapi.views.forms import JoinFormRequest

# Only used for dev with Minio. Don't set in deployed or unit testing envs
JOIN_RECORD_ENDPOINT = os.environ.get("S3_ENDPOINT", None)

JOIN_RECORD_BUCKET_NAME = os.environ.get("JOIN_RECORD_BUCKET_NAME")
JOIN_RECORD_PREFIX = os.environ.get("JOIN_RECORD_PREFIX", "sample-basename")


class SubmissionStage(Enum):
    PRE = "pre"
    POST = "post"


@dataclass
class JoinRecord(JoinFormRequest):
    version: int
    uuid: str  # XXX (wdn): Should we consider making this a UUID?
    submission_time: str
    code: str
    replayed: int
    install_number: Optional[int]


# XXX (wdn): Not sure if im gonna use this
@dataclass
class JoinRecordV3Key:
    prefix: str  # Specifies if the record was submitted from dev3, prod2, etc
    version: int  # Version of Join Record. V1, V2, and V3 (for now)
    submission_stage: SubmissionStage  # Pre, Post, Replayed
    submission_time: datetime.datetime  # When
    uuid_snippet: str  # First quartet (2nd group) of the UUID to ensure uniqueness


# v3
def s3_content_to_join_record(object_key: str, content: str) -> JoinRecord:
    content_json = json.loads(content)
    mapped_content_json = {key.name: content_json.get(key.name) for key in fields(JoinRecord)}
    join_record = JoinRecord(**mapped_content_json)

    # Convert S3 path to datetime
    # "dev-join-form-submissions/v3/post/2024/10/28/12/27/00/abcd.json"
    datetime_components = object_key.split(".")[0].split("/")[3:9]
    year, month, day, hour, minute, second = map(int, datetime_components)
    result_datetime = datetime.datetime(year, month, day, hour, minute, second)
    join_record.submission_time = result_datetime.isoformat()
    return join_record


class JoinRecordProcessor:
    def __init__(self) -> None:
        if not JOIN_RECORD_BUCKET_NAME:
            raise EnvironmentError("Did not find JOIN_RECORD_BUCKET_NAME")

        if not JOIN_RECORD_PREFIX:
            raise EnvironmentError("Did not find JOIN_RECORD_PREFIX")

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

    def get_all(
        self, since: Optional[datetime.datetime] = None, submission_prefix: SubmissionStage = SubmissionStage.POST
    ) -> list[JoinRecord]:
        prefix = f"{JOIN_RECORD_PREFIX}/v3/{submission_prefix.value}"
        start_after = (
            since.strftime(f"{JOIN_RECORD_PREFIX}/v3/{submission_prefix.value}/%Y/%m/%d/%H/%M/%S")
            if isinstance(since, datetime.datetime)
            else ""
        )
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=JOIN_RECORD_BUCKET_NAME,
                Prefix=prefix,
                StartAfter=start_after,
            )
        except ClientError as e:
            # This will raise ClientError (AccessDenied) if the bucket doesn't exist.
            logging.exception(
                f"Error accessing bucket. Check bucket name. JOIN_RECORD_BUCKET_NAME={JOIN_RECORD_BUCKET_NAME}"
            )
            raise e

        contents = response.get("Contents")
        if not contents:
            logging.error(
                f"Found no records. Check Prefix or StartAfter parameters. Prefix={prefix}, StartAfter={start_after}"
            )
            return []

        join_records = []
        for obj in contents:
            object_key = obj["Key"]

            # Get object content
            content_object = self.s3_client.get_object(Bucket=JOIN_RECORD_BUCKET_NAME, Key=object_key)
            content = content_object["Body"].read().decode("utf-8")

            join_records.append(s3_content_to_join_record(object_key, content))

        return join_records

    # I hardcoded the folder prefix to prevent any shenanigans
    def flush_test_data(self) -> None:
        # This should be the same as MOCK_JOIN_RECORD_PREFIX
        folder_path = "join-record-test"

        objects_to_delete = self.s3_client.list_objects_v2(Bucket=JOIN_RECORD_BUCKET_NAME, Prefix=folder_path)

        if "Contents" in objects_to_delete:
            delete_keys = [{"Key": obj["Key"]} for obj in objects_to_delete["Contents"]]

            self.s3_client.delete_objects(Bucket=JOIN_RECORD_BUCKET_NAME, Delete={"Objects": delete_keys})
            print(f"Folder '{folder_path}' deleted from bucket '{JOIN_RECORD_BUCKET_NAME}'.")
        else:
            print(f"No objects found in folder '{folder_path}'.")

    # Examines join records from pre- and post-submission and ensures a copy is
    # present in each. If one is missing from the post-submission, indicating there
    # was some deeper problem in submitting to MeshDB, we backfill it into
    # the post-submission list we return
    def ensure_pre_post_consistency(self, since: datetime.datetime) -> dict[str, JoinRecord]:
        # Get join records from both pre and post submissions so we can make sure
        # there are no discrepancies

        # Grab a copy of pre, post, and replayed submissions
        # Convert the lists to dictionaries to make them easier to search by UUID
        pre_join_records_dict: dict[str, JoinRecord] = {}
        for record in self.get_all(since, SubmissionStage.PRE):
            if record.version >= 2:
                pre_join_records_dict[record.uuid] = record

        post_join_records_dict: dict[str, JoinRecord] = {}
        for record in self.get_all(since, SubmissionStage.POST):
            if record.version >= 2:
                post_join_records_dict[record.uuid] = record

        # For each pre-submission record, there should exist a post-submission
        # record. If the post-submission record is missing, log a warning and add
        # the pre-submission record to the post-submission dictionary so it is covered
        # by the command.
        for uuid, record in pre_join_records_dict.items():
            if post_join_records_dict.get(uuid):
                continue
            key_for_warning = self.get_key(record, SubmissionStage.PRE)
            logging.warning(
                "Did not find a corresponding post-submission join record for "
                f"pre-submission join record {key_for_warning}. Will supplement post-submission records."
            )
            post_join_records_dict[uuid] = record

        # This should never happen, but theoretically we could fail to submit the pre-submisison record,
        # successfully(?) submit the join form, then successfully submit the post-submission record.
        # If that happens, we'd like to know about it, but there's not much we can or should do since the
        # post-submission records ought to be the source of truth.
        for uuid, record in post_join_records_dict.items():
            if pre_join_records_dict.get(uuid):
                continue
            key_for_warning = self.get_key(record, SubmissionStage.POST)
            logging.warning(
                "Did not find a corresponding pre-submission join record for "
                f"pre-submission join record {key_for_warning}. THIS SHOULD NEVER HAPPEN."
            )

        return post_join_records_dict

    @staticmethod
    def get_key(join_record: JoinRecord, stage: SubmissionStage) -> str:
        submission_time = datetime.datetime.fromisoformat(join_record.submission_time)
        uuid_snippet = join_record.uuid.split("-")[1]

        return submission_time.strftime(f"{JOIN_RECORD_PREFIX}/v3/{stage.value}/%Y/%m/%d/%H/%M/%S/{uuid_snippet}.json")
