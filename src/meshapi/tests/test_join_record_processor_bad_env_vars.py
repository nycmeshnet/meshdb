from unittest.mock import patch

from botocore.exceptions import ClientError
from django.test import TestCase

from meshapi.util.join_records import JoinRecordProcessor


class TestJoinRecordProcessorBadEnvVars(TestCase):
    @patch("meshapi.util.join_records.JOIN_RECORD_BUCKET_NAME", "")
    def test_missing_bucket_name(self):
        with self.assertRaises(EnvironmentError):
            JoinRecordProcessor()

    @patch("meshapi.util.join_records.JOIN_RECORD_PREFIX", "")
    def test_missing_prefix(self):
        with self.assertRaises(EnvironmentError):
            JoinRecordProcessor()

    @patch("meshapi.util.join_records.JOIN_RECORD_BUCKET_NAME", "chom")
    def test_bad_bucket_name(self):
        with self.assertRaises(ClientError):
            JoinRecordProcessor().get_all()
