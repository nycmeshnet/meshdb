import os
from unittest import mock, skip

from django.test import TestCase
from flags.state import enable_flag

from meshapi.tasks import reset_dev_database, run_database_backup, run_update_from_uisp, run_update_panoramas


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
            [
                mock.call("dbrestore", "--noinput", "--database", "default"),
                mock.call("scramble_members", "--noinput"),
            ]
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


class TestRunUpdateFromUispTask(TestCase):
    @mock.patch("meshapi.tasks.sync_link_table_into_los_objects")
    @mock.patch("meshapi.tasks.import_and_sync_uisp_links")
    @mock.patch("meshapi.tasks.import_and_sync_uisp_devices")
    @mock.patch("meshapi.tasks.get_uisp_links")
    @mock.patch("meshapi.tasks.get_uisp_devices")
    def test_run_update_from_uisp(
        self,
        mock_get_uisp_devices,
        mock_get_uisp_links,
        mock_import_devices,
        mock_import_links,
        mock_sync_los,
    ):
        uisp_devices = [{"identification": {"id": "uisp-uuid1", "type": "blackBox"}}]
        uisp_links = [{"id": "uisp-link-uuid1"}]
        mock_get_uisp_devices.return_value = uisp_devices
        mock_get_uisp_links.return_value = uisp_links

        enable_flag("TASK_ENABLED_SYNC_WITH_UISP")
        run_update_from_uisp()

        # The device list is fetched once and shared with the link import, so the link import
        # can tell which links UISP can't detect
        mock_get_uisp_devices.assert_called_once_with()
        mock_import_devices.assert_called_once_with(uisp_devices)
        mock_import_links.assert_called_once_with(uisp_links, uisp_devices=uisp_devices)
        mock_sync_los.assert_called_once_with()


@skip(reason="Currently fails using both the unittest and pytest test runners")
@mock.patch("meshapi.util.panoramas.get_head_tree_sha", return_value="mockedsha")
@mock.patch(
    "meshapi.util.panoramas.list_files_in_git_directory",
    return_value=["713a.jpg", "713b.jpg"],
)
class TestUpdatePanoramasTask(TestCase):
    def test_update_panoramas_task(self):
        run_update_panoramas()
