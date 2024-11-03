import os
from unittest.mock import patch

from django.core import management
from django.test import TestCase

from meshapi.models.install import Install
from meshapi.util.join_records import JoinRecord, JoinRecordProcessor, s3_content_to_join_record

MOCK_JOIN_RECORD_PREFIX = "join-record-test"


# Integration test to ensure that we can fetch JoinRecords from an S3 bucket,
# replay them into the join form, and insert the objects we expect.
# We should test a happy case, a case when the JoinRecord is bad (like a JoinRecord
# somehow from Russia), and maybe mock a MeshDB 500 that just ends in us putting
# the data back.
class TestReplayJoinRecords(TestCase):
    def setUp(self) -> None:
        p = JoinRecordProcessor()
        p.flush_test_data()

    def tearDown(self) -> None:
        p = JoinRecordProcessor()
        p.flush_test_data()

    # This is just to make codecov happy
    def test_s3_content_to_join_record(self):
        sample_key = "dev-join-form-submissions/2024/11/01/11/33/49.json"
        sample_s3_content = """{"first_name":"Jon","last_name":"Smith","email_address":"js@gmail.com","phone_number":"+1 585-475-2411","street_address":"197 Prospect Place","apartment":"1","city":"Brooklyn","state":"NY","zip_code":"11238","roof_access":true,"referral":"I googled it.","ncl":true,"trust_me_bro":false,"code":"201","replayed":0,"install_number":1002}"""
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
        )
        join_record = s3_content_to_join_record(sample_key, sample_s3_content)
        try:
            self.assertEqual(join_record, sample_join_record, "Join Records do not match")
        except AssertionError as e:
            print(sample_join_record)
            print(join_record)
            raise e

    @patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", MOCK_JOIN_RECORD_PREFIX)
    def test_replay_join_records(self):
        sample_join_records: dict[str, JoinRecord] = {
            f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/30/12/34/56.json": JoinRecord(
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
                submission_time="2024-10-30T12:34:56",
                code="500",
                replayed=0,
                install_number=None,
            ),
            f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/30/12/34/57.json": JoinRecord(
                first_name="Jon",
                last_name="Smith",
                email_address="js@gmail.com",
                phone_number="+1 585-475-2411",
                street_address="711 Hudson Street",
                city="Hoboken",
                state="NJ",
                zip_code="07030",
                apartment="",
                roof_access=True,
                referral="Totally faked mocked join record.",
                ncl=True,
                trust_me_bro=False,
                submission_time="2024-10-30T12:34:57",
                code="400",
                replayed=1,
                install_number=None,
            ),
        }

        # Load the samples into S3
        p = JoinRecordProcessor()
        for key, record in sample_join_records.items():
            print(key)
            p.upload(record, key)

        # Replay the records
        management.call_command("replay_join_records", "--noinput")

        # FIXME (wdn): I had to combine these tests because I couldn't figure
        # out how to make the mock atomic and they kept poisoning each other.
        records = p.get_all()

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
