import os
from datetime import datetime
from unittest import mock

from django.test import TestCase

from meshapi.tasks import reset_dev_database, run_database_backup
from meshapi.util.task_utils import get_most_recent_object
from meshdb.settings import MESHDB_ENVIRONMENT


# Not intended to test the functionality of, say, dbbackup. More intended
# to test the environment logic.
class TestTasks(TestCase):
    def setUp(self):
        pass

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod1")
    def test_run_database_backup(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        self.assertTrue(run_database_backup())

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_database_backup_not_prod(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        self.assertFalse(run_database_backup())

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod1")
    def test_run_database_backup_no_creds(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        self.assertFalse(run_database_backup())

    @mock.patch("meshapi.util.task_utils.get_most_recent_object")
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database(self, mock_call_command_func, mock_get_most_recent_object_func):
        latest_backup = "not-a-bucket/notprod1/not-a-backup.psql.bin"
        mock_get_most_recent_object_func.return_value = latest_backup
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        self.assertTrue(reset_dev_database())
        mock_call_command_func.assert_has_calls(
            [mock.call("dbrestore", "--noinput", "-i", latest_backup), mock.call("scramble_members", "--noinput")]
        )

    @mock.patch("meshapi.util.task_utils.get_most_recent_object")
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod1")
    def test_run_reset_dev_database_not_dev(self, mock_call_command_func, mock_get_most_recent_object_func):
        latest_backup = "not-a-bucket/notprod1/not-a-backup.psql.bin"
        mock_get_most_recent_object_func.return_value = latest_backup
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        self.assertFalse(reset_dev_database())

    @mock.patch("meshapi.util.task_utils.get_most_recent_object")
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database_no_creds(self, mock_call_command_func, mock_get_most_recent_object_func):
        latest_backup = "not-a-bucket/notprod1/not-a-backup.psql.bin"
        mock_get_most_recent_object_func.return_value = latest_backup
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        self.assertFalse(reset_dev_database())


class TestTaskUtils(TestCase):
    def setUp(self):
        pass

    @mock.patch("boto3.client")
    def test_get_most_recent_object(self, mock_boto_client):
        mock_s3_client = mock.MagicMock()
        key = "not-a-backup.psql.bin"
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": key,
                    "LastModified": datetime(2015, 1, 1),
                    "ETag": "string",
                    "ChecksumAlgorithm": [
                        "SHA256",
                    ],
                    "Size": 123,
                    "StorageClass": "STANDARD",
                    "Owner": {"DisplayName": "string", "ID": "string"},
                    "RestoreStatus": {"IsRestoreInProgress": False, "RestoreExpiryDate": datetime(2015, 1, 1)},
                },
            ],
        }

        mock_boto_client.return_value = mock_s3_client

        backup = get_most_recent_object("not-a-bucket", "notprod1/")
        self.assertEqual(backup, key)

    @mock.patch("boto3.client")
    def test_get_most_recent_object_empty_bucket(self, mock_boto_client):
        mock_s3_client = mock.MagicMock()
        mock_s3_client.list_objects_v2.return_value = {}
        mock_boto_client.return_value = mock_s3_client

        backup = get_most_recent_object("not-a-bucket", "notprod1/")
        self.assertEqual(backup, None)
