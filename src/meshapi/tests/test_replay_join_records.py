
import os
from unittest.mock import patch
from django.core import management
from django.test import TestCase

from meshapi.util.join_records import MockJoinRecordProcessor

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

    @patch('meshapi.util.join_records.JoinRecordProcessor')
    def test_happy_replay_join_records(self, MockJoinRecordProcessorClass):
        sample_join_records = {}
        MockJoinRecordProcessorClass.side_effect = lambda *args, **kwargs: MockJoinRecordProcessor(data=sample_join_records)
        management.call_command("replay_join_records", "--noinput")
        

