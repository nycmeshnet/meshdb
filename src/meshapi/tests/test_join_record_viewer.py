import logging
from unittest.mock import patch
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.test import Client, TestCase
from moto import mock_aws

from meshapi.tests.sample_join_records import (
    MOCK_JOIN_RECORD_PREFIX,
    basic_sample_post_submission_join_records,
    basic_sample_pre_submission_join_records,
)
from meshapi.util.join_records import JOIN_RECORD_BUCKET_NAME, JoinRecordProcessor


@mock_aws
@patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
class TestJoinRecordViewer(TestCase):
    c = Client()
    p = JoinRecordProcessor()

    def setUp(self) -> None:
        print(JOIN_RECORD_BUCKET_NAME)
        self.p.s3_client.create_bucket(Bucket=JOIN_RECORD_BUCKET_NAME)
        self.p.flush_test_data()

        # Load the samples into S3
        for key, record in basic_sample_pre_submission_join_records.items():
            self.p.upload(record, key)

        for key, record in basic_sample_post_submission_join_records.items():
            self.p.upload(record, key)

        self.admin_user = User.objects.create_superuser(
            username="admin", password="admin_password", email="admin@example.com"
        )
        self.c.login(username="admin", password="admin_password")



    def tearDown(self) -> None:
        self.p.flush_test_data()

    def test_view_join_records(self):
        response = self.c.get("/join-records/view/?since=2024-09-30T00:00:00")
        self.assertEqual(200, response.status_code)

        decoded = response.content.decode()
        soup = BeautifulSoup(decoded, "html.parser")
        record_table = soup.find(id="record_table")
        self.assertIsNotNone(record_table)
        for _, v in basic_sample_pre_submission_join_records.items():
            logging.info(v.uuid)
            record_row = soup.find(id=v.uuid)

            # One of these will be None because it got submitted successfully.
            if v.uuid == "109ede4d-0f84-4044-a14c-090121f0c7d4":
                self.assertIsNone(record_row)
                continue

            self.assertIsNotNone(record_row)

    def test_view_all_join_records(self):
        response = self.c.get("/join-records/view/?since=2024-09-30T00:00:00&all=True")
        self.assertEqual(200, response.status_code)

        decoded = response.content.decode()
        soup = BeautifulSoup(decoded, "html.parser")
        record_table = soup.find(id="record_table")
        self.assertIsNotNone(record_table)
        for _, v in basic_sample_pre_submission_join_records.items():
            logging.info(v.uuid)
            record_row = soup.find(id=v.uuid)
            self.assertIsNotNone(record_row)
