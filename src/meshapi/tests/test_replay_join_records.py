import json
from datetime import datetime, timedelta
from unittest.mock import patch

from django.core import management
from django.test import TestCase

from meshapi.models.install import Install
from meshapi.tests.sample_join_records import MOCK_JOIN_RECORD_PREFIX, basic_sample_join_records
from meshapi.util.join_records import JoinRecord, JoinRecordProcessor, s3_content_to_join_record


# Integration test to ensure that we can fetch JoinRecords from an S3 bucket,
# replay them into the join form, and insert the objects we expect.
# We should test a happy case, a case when the JoinRecord is bad (like a JoinRecord
# somehow from Russia), and maybe mock a MeshDB 500 that just ends in us putting
# the data back.
class TestReplayJoinRecords(TestCase):
    p = JoinRecordProcessor()

    def setUp(self) -> None:
        self.p.flush_test_data()

    def tearDown(self) -> None:
        self.p.flush_test_data()

    @patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
    def test_get_all_since(self):
        # Load the samples into S3
        for key, record in basic_sample_join_records.items():
            self.p.upload(record, key)

        records_since = self.p.get_all(since=datetime.fromisoformat("2024-10-01 00:00:00"))

        self.assertEqual(len(records_since), 2)

        self.assertEqual(
            basic_sample_join_records[f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/28/12/34/56.json"], records_since[0]
        )
        self.assertEqual(
            basic_sample_join_records[f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/30/12/34/57.json"], records_since[1]
        )

        records_since = self.p.get_all(since=datetime.fromisoformat("2024-10-29 00:00:00"))
        self.assertEqual(len(records_since), 1)

        self.assertEqual(
            basic_sample_join_records[f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/30/12/34/57.json"], records_since[0]
        )

    @patch("meshapi.management.commands.replay_join_records.Command.past_week")
    @patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
    def test_replay_basic_join_records(self, past_week_function):
        halloween_minus_one_week = datetime(2024, 10, 31, 8, 0, 0, 0) - timedelta(days=7)
        past_week_function.return_value = halloween_minus_one_week

        # Load the samples into S3
        for key, record in basic_sample_join_records.items():
            self.p.upload(record, key)

        # Replay the records (this should get from the last week (halloween -7 days))
        management.call_command("replay_join_records", "--noinput", "--write")

        records = self.p.get_all()

        self.assertEqual(2, len(records), "Got unexpected number of records in mocked S3 bucket.")

        # The first record should have been fine and dandy
        r = records[0]
        expected_code = "201"
        self.assertEqual(
            expected_code,
            r.code,
            f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.code}",
        )
        self.assertEqual(1, r.replayed, "Did not get expected replay count.")

        # XXX (wdn): Assert that replayed data was correctly replayed.
        # It's probably good enough to do this with the install number,
        # but it would be nice to have the UUIDs that get returned.
        install = Install.objects.get(install_number=r.install_number)
        self.assertEqual("Jon Smith", install.member.name, "Did not get expected name for submitted install.")
        self.assertEqual(
            "197 Prospect Place",
            install.building.street_address,
            "Did not get expected street address for submitted install.",
        )

        # The next record should have failed because it lives in NJ
        r = records[1]
        expected_code = "400"
        self.assertEqual(
            expected_code,
            r.code,
            f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.code}",
        )
        self.assertEqual(2, r.replayed, "Did not get expected replay count.")
        self.assertEqual(None, r.install_number, "Install Number is not None.")

    # This is just to make codecov happy
    def test_s3_content_to_join_record(self):
        sample_key = "dev-join-form-submissions/2024/11/01/11/33/49.json"

        # We're converting this...
        sample_join_record_s3_content = json.dumps(
            {
                "first_name": "Jon",
                "last_name": "Smith",
                "email_address": "js@gmail.com",
                "phone_number": "+1 585-475-2411",
                "street_address": "197 Prospect Place",
                "apartment": "1",
                "city": "Brooklyn",
                "state": "NY",
                "zip_code": "11238",
                "roof_access": True,
                "referral": "I googled it.",
                "ncl": True,
                "trust_me_bro": False,
                "code": "201",
                "replayed": 0,
                "install_number": 1002,
                "recaptcha_checkbox_token": None,
                "recaptcha_invisible_token": None,
            }
        )

        # To this.
        sample_join_record: JoinRecord = JoinRecord(
            first_name="Jon",
            last_name="Smith",
            email_address="js@gmail.com",
            phone_number="+1 585-475-2411",
            street_address="197 Prospect Place",
            apartment="1",
            city="Brooklyn",
            state="NY",
            zip_code="11238",
            roof_access=True,
            referral="I googled it.",
            ncl=True,
            trust_me_bro=False,
            submission_time="2024-11-01T11:33:49",
            code="201",
            replayed=0,
            install_number=1002,
            recaptcha_checkbox_token=None,
            recaptcha_invisible_token=None,
        )
        join_record = s3_content_to_join_record(sample_key, sample_join_record_s3_content)
        try:
            self.assertEqual(join_record, sample_join_record, "Join Records do not match")
        except AssertionError as e:
            print(sample_join_record)
            print(join_record)
            raise e
