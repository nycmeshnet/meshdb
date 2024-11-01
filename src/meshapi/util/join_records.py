import datetime
import json
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Optional

import boto3
from botocore.client import ClientError, Config

from meshapi.views.forms import JoinFormRequest

JOIN_RECORD_ENDPOINT = os.environ.get("JOIN_RECORD_ENDPOINT")
JOIN_RECORD_BUCKET_NAME = os.environ.get("JOIN_RECORD_BUCKET_NAME")
JOIN_RECORD_BASE_NAME = os.environ.get("JOIN_RECORD_BASE_NAME", "sample-basename")
JOIN_RECORD_ACCESS_KEY = os.environ.get("JOIN_RECORD_ACCESS_KEY")
JOIN_RECORD_SECRET_KEY = os.environ.get("JOIN_RECORD_SECRET_KEY")


@dataclass
class JoinRecord(JoinFormRequest):
    submission_time: str
    code: str
    replayed: int
    install_number: Optional[int]


class JoinRecordProcessorInterface(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def upload(self, join_record: JoinRecord, key: str) -> None:
        pass

    @abstractmethod
    def get_all(self) -> list[JoinRecord]:
        pass


class JoinRecordProcessor(JoinRecordProcessorInterface):
    def __init__(self) -> None:
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=JOIN_RECORD_ENDPOINT,
            aws_access_key_id=JOIN_RECORD_ACCESS_KEY,
            aws_secret_access_key=JOIN_RECORD_SECRET_KEY,
            config=Config(signature_version="s3v4"),  # Ensure S3 signature v4 is used
        )

    def upload(self, join_record: JoinRecord, key: str) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(str.encode(json.dumps(join_record)))
        try:
            self.s3_client.upload_file(tmp, JOIN_RECORD_BUCKET_NAME, key)
        except ClientError as e:
            logging.error(e)

    def get_all(self) -> list[JoinRecord]:
        response = self.s3_client.list_objects_v2(Bucket=JOIN_RECORD_BUCKET_NAME)

        join_records = []

        # Loop through each object and get its contents
        if "Contents" in response:
            for obj in response["Contents"]:
                object_key = obj["Key"]

                # Get object content
                content_object = self.s3_client.get_object(Bucket=JOIN_RECORD_BUCKET_NAME, Key=object_key)
                content = content_object["Body"].read().decode("utf-8")
                content_json = json.loads(content)
                mapped_content_json = {key.name: content_json.get(key.name) for key in fields(JoinRecord)}
                join_record = JoinRecord(**mapped_content_json)

                # Convert S3 path to datetime
                # "dev-join-form-submissions/2024/10/28/12/27/00.json"
                datetime_components = object_key.split(".")[0].split("/")[1:]
                year, month, day, hour, minute, second = map(int, datetime_components)
                result_datetime = datetime.datetime(year, month, day, hour, minute, second)
                join_record.submission_time = result_datetime.isoformat()

                join_records.append(join_record)
        else:
            print("Bucket is empty or does not exist.")

        return join_records


class MockJoinRecordProcessor(JoinRecordProcessorInterface):
    def __init__(self, data: dict[str, JoinRecord]) -> None:
        self.bucket_name: str = "mock_bucket"
        # Store join record by S3 key and value.
        self.bucket: dict[str, JoinRecord] = data

    def upload(self, join_record: JoinRecord, key: str) -> None:
        self.bucket[key] = join_record

    def get_all(self) -> list[JoinRecord]:
        return list(self.bucket.values())
