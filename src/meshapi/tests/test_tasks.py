import os
from unittest import mock

from django.test import TestCase
from flags.state import enable_flag

from meshapi.tasks import reset_dev_database, run_database_backup, run_update_panoramas


# Not intended to test the functionality of, say, dbbackup. More intended
# to test the environment logic.
class TestRunDatabaseBackupTask(TestCase):
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_database_backup(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        enable_flag("TASK_ENABLED_RUN_DATABASE_BACKUP")
        run_database_backup()
        mock_call_command_func.assert_has_calls([mock.call("dbbackup")])

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_database_backup_not_prod(self, mock_call_command_func):
        # This test will pass because dev is allowed to run backups. We should
        # be careful to keep that flag turned off in dev.
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        enable_flag("TASK_ENABLED_RUN_DATABASE_BACKUP")
        run_database_backup()
        mock_call_command_func.assert_has_calls([mock.call("dbbackup")])

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_database_backup_no_creds(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        enable_flag("TASK_ENABLED_RUN_DATABASE_BACKUP")
        with self.assertRaises(ValueError):
            run_database_backup()


class TestResetDevDatabaseTask(TestCase):
    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        enable_flag("TASK_ENABLED_RESET_DEV_DATABASE")
        reset_dev_database()
        mock_call_command_func.assert_has_calls(
            [mock.call("dbrestore", "--noinput", "--database", "default"), mock.call("scramble_members", "--noinput")]
        )

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "prod")
    def test_run_reset_dev_database_not_dev(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "alsofake"
        enable_flag("TASK_ENABLED_RESET_DEV_DATABASE")
        with self.assertRaises(EnvironmentError):
            reset_dev_database()

    @mock.patch("django.core.management.call_command")
    @mock.patch("meshapi.tasks.MESHDB_ENVIRONMENT", "dev3")
    def test_run_reset_dev_database_no_creds(self, mock_call_command_func):
        os.environ["AWS_ACCESS_KEY_ID"] = ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = ""
        enable_flag("TASK_ENABLED_RESET_DEV_DATABASE")
        with self.assertRaises(ValueError):
            reset_dev_database()


@mock.patch("meshapi.util.panoramas.get_head_tree_sha", return_value="mockedsha")
@mock.patch("meshapi.util.panoramas.list_files_in_git_directory", return_value=["713a.jpg", "713b.jpg"])
class TestUpdatePanoramasTask:
    def test_update_panoramas_task(self):
        run_update_panoramas()
