import datetime
import os
from unittest.mock import patch
from django.core import management
from django.test import TestCase

from meshapi.util.join_records import JOIN_RECORD_BASE_NAME, JoinRecord, MockJoinRecordProcessor
from meshapi.views.forms import process_join_form


# Integration test to ensure that we can fetch JoinRecords from an S3 bucket,
# replay them into the join form, and insert the objects we expect.
# We should test a happy case, a case when the JoinRecord is bad (like a JoinRecord
# somehow from Russia), and maybe mock a MeshDB 500 that just ends in us putting
# the data back.
class TestReplayJoinRecords(TestCase):
    def setUp(self) -> None:
        # Create S3 bucket in MinIO, put some sample data in there
        return super().setUp()

    def tearDown(self) -> None:
        # Delete S3 Bucket
        return super().tearDown()

    @patch("meshapi.views.forms.process_join_form", wraps=process_join_form)
    @patch("meshapi.util.join_records.JoinRecordProcessor")
    def test_happy_replay_join_records(self, MockJoinRecordProcessorClass, mock_process_join_form):
        os.environ[JOIN_RECORD_BASE_NAME] = "mock-join-record-test"
        sample_join_records = {
            f"{JOIN_RECORD_BASE_NAME}/2024/10/30/12/34/56.json": JoinRecord(
                first_name="Jon",
                last_name="Smith",
                email_address="js@gmail.com",
                phone_number="+1 585-475-2411",
                street_address="197 Prospect Place",
                city="Brooklyn",
                state="NY",
                zip_code="11238",
                apartment="1",
                roof_access=True,
                referral="Totally faked mocked join record.",
                ncl=True,
                trust_me_bro=False,
                submission_time=datetime.datetime(2024, 10, 30, 12, 34, 56),
                code="500",
                replayed=0,
                replay_code="",
            )
        }


        # Set up a mocked instance of the bucket
        mock_processor = MockJoinRecordProcessor(
            data=sample_join_records
        )
        MockJoinRecordProcessorClass.side_effect = lambda *args, **kwargs: mock_processor 

        # Replay the records
        management.call_command("replay_join_records", "--noinput")

        records = mock_processor.get_all()
        self.assertEqual(1, len(records), f"Got unexpected number of records in mocked S3 bucket.")
        for r in records:
            expected_code = "201"
            self.assertEqual(expected_code, r.replay_code, f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.replay_code}")
            self.assertEqual(1, r.replayed, f"Did not get expected replay count.")

        # TODO: Assert that replayed data was correctly replayed. I want the HTTP code,
        # and I want the UUIDs so I can look it up in the DB and verify it.

        join_form_response = mock_process_join_form.return_value
        print(join_form_response)
