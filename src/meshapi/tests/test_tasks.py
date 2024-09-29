import os
from unittest import mock

from django.test import TestCase

from meshapi.tasks import reset_dev_database, run_database_backup


# Not intended to test the functionality of, say, dbbackup. More intended
# to test the environment logic.
class TestRunDatabaseBackupTask(TestCase):
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_database_backup(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        run_database_backup()
        mock_call_command_func.assert_has_calls([mock.call("dbbackup")])

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_database_backup_not_prod(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        with self.assertRaises(EnvironmentError):
            run_database_backup()

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_database_backup_no_creds(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        with self.assertRaises(ValueError):
            run_database_backup()


class TestResetDevDatabaseTask(TestCase):
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        reset_dev_database()
        mock_call_command_func.assert_has_calls(
            [mock.call("dbrestore", "--noinput", "--database", "default"), mock.call("scramble_members", "--noinput")]
        )

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_reset_dev_database_not_dev(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        with self.assertRaises(EnvironmentError):
            reset_dev_database()

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database_no_creds(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        with self.assertRaises(ValueError):
            reset_dev_database()
