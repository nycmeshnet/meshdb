import json
from datetime import datetime, timedelta
from unittest.mock import patch

from django.core import management
from django.test import TestCase
from moto import mock_aws

from meshapi.models.install import Install
from meshapi.tests.sample_join_records import (
    MOCK_JOIN_RECORD_PREFIX,
    basic_sample_post_submission_join_records,
    basic_sample_pre_submission_join_records,
)
from meshapi.util.join_records import (
    JOIN_RECORD_BUCKET_NAME,
    JoinRecord,
    JoinRecordProcessor,
    SubmissionStage,
    s3_content_to_join_record,
)
from meshapi.validation import NYCAddressInfo


# Integration test to ensure that we can fetch JoinRecords from an S3 bucket,
# replay them into the join form, and insert the objects we expect.
# We should test a happy case, a case when the JoinRecord is bad (like a JoinRecord
# somehow from Russia), and maybe mock a MeshDB 500 that just ends in us putting
# the data back.
@mock_aws
@patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
class TestReplayJoinRecords(TestCase):
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

    def tearDown(self) -> None:
        self.p.flush_test_data()

    # I broke the help menu once upon a time so I need to make sure this works.
    def test_help_works(self):
        with self.assertRaises(SystemExit):
            management.call_command("replay_join_records", "--help")

    def test_list_records(self):
        management.call_command("replay_join_records")

    def test_get_all_since(self):
        records_since = self.p.get_all(since=datetime.fromisoformat("2024-10-01 00:00:00"))

        self.assertEqual(len(records_since), 4)

        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/28/12/34/56/ec7b.json"
            ],
            records_since[0],
        )
        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/34/57/0490.json"
            ],
            records_since[1],
        )
        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/34/59/7cd3.json"
            ],
            records_since[2],
        )
        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/35/00/0f84.json"
            ],
            records_since[3],
        )

        records_since = self.p.get_all(since=datetime.fromisoformat("2024-10-29 00:00:00"))
        self.assertEqual(len(records_since), 3)

        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/34/57/0490.json"
            ],
            records_since[0],
        )
        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/34/59/7cd3.json"
            ],
            records_since[1],
        )
        self.assertEqual(
            basic_sample_post_submission_join_records[
                f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/10/30/12/35/00/0f84.json"
            ],
            records_since[2],
        )

    # This is just to make codecov happy
    def test_s3_content_to_join_record(self):
        sample_key = f"{MOCK_JOIN_RECORD_PREFIX}/v3/post/2024/11/01/11/33/49/0490.json"

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
                "version": 3,
                "uuid": "1a55b949-0490-4b78-a2e8-10aea41d6f1d",
                "code": "201",
                "replayed": 0,
                "install_number": 1002,
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
            version=3,
            uuid="1a55b949-0490-4b78-a2e8-10aea41d6f1d",
            submission_time="2024-11-01T11:33:49",
            code="201",
            replayed=0,
            install_number=1002,
        )
        join_record = s3_content_to_join_record(sample_key, sample_join_record_s3_content)
        try:
            self.assertEqual(join_record, sample_join_record, "Join Records do not match")
        except AssertionError as e:
            print(sample_join_record)
            print(join_record)
            raise e

    @patch("meshapi.management.commands.replay_join_records.Command.past_week")
    @patch("meshapi.views.forms.geocode_nyc_address")
    def test_replay_join_records_with_write(self, mock_geocode_func, past_week_function):
        halloween_minus_one_week = datetime(2024, 10, 31, 8, 0, 0, 0) - timedelta(days=7)
        past_week_function.return_value = halloween_minus_one_week
        mock_geocode_func.side_effect = [
            NYCAddressInfo("197 Prospect Place", "Brooklyn", "NY", "11238"),
            ValueError("NJ not allowed yet!"),
            NYCAddressInfo("99 Kane Street", "Brooklyn", "NY", "11231"),
            # These next two are both for the 4th join record (Rachel Doe) that got 409'ed
            NYCAddressInfo("99 Kane Street", "Brooklyn", "NY", "11231"),
            NYCAddressInfo("99 Kane Street", "Brooklyn", "NY", "11231"),
        ]

        # Replay the records (this should get from the last week (halloween -7 days))
        management.call_command("replay_join_records", "--noinput", "--write")

        records = self.p.get_all(submission_prefix=SubmissionStage.POST)

        # After replaying, ensure we have the right number of post-submission records.
        # The replay script should've only updated the ones that were already there,
        # inserted the "pre" submission one that was missing, and ignored the 201.
        self.assertEqual(5, len(records), "Got unexpected number of records in mocked S3 bucket.")

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

        # Pre-submission with the missing post-submission. This one
        # should also work fine
        r = records[2]
        expected_code = "201"
        self.assertEqual(
            expected_code,
            r.code,
            f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.code}",
        )
        self.assertEqual(1, r.replayed, "Did not get expected replay count.")
        install = Install.objects.get(install_number=r.install_number)
        self.assertEqual("Benjamin Doe", install.member.name, "Did not get expected name for submitted install.")
        self.assertEqual(
            "99 Kane Street",
            install.building.street_address,
            "Did not get expected street address for submitted install.",
        )

        # Request was submitted while MeshDB was hard down. Should've gotten a 409
        # and then a 201
        r = records[3]
        expected_code = "201"
        self.assertEqual(
            expected_code,
            r.code,
            f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.code}",
        )
        self.assertEqual(1, r.replayed, "Did not get expected replay count.")
        install = Install.objects.get(install_number=r.install_number)
        self.assertEqual("Rachel Doe", install.member.name, "Did not get expected name for submitted install.")
        self.assertEqual(
            "99 Kane Street",
            install.building.street_address,
            "Did not get expected street address for submitted install.",
        )

        # Ensure we didn't touch the 201'ed request (Doesn't actually exist in the DB
        # but ¯\_(ツ)_/¯)
        r = records[4]
        expected_code = "201"
        self.assertEqual(
            expected_code,
            r.code,
            f"Did not find correct replay code in mocked S3 bucket. Expected: {expected_code}, Got: {r.code}",
        )
        self.assertEqual(0, r.replayed, "Did not get expected replay count.")
