import logging
import os

from celery.schedules import crontab
from django.core import management

from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links
from meshapi.util.uisp_import.sync_handlers import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)
from meshapi.views.panoramas import sync_github_panoramas
from meshdb.celery import app as celery_app


@celery_app.task
def run_database_backup() -> None:
    # Don't run a backup unless it's prod1
    if os.environ.get("MESHDB_ENVIRONMENT") != "prod1":
        logging.warn(f"Not running database backup. This environment is: \"{os.environ.get("MESHDB_ENVIRONMENT", "")}\"")
        return

    logging.info("Running database backup task")
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        logging.error("Could not run backup. Missing AWS credentials!")
        return

    try:
        management.call_command("dbbackup")
    except Exception as e:
        logging.exception(e)
        raise e

@celery_app.task
def reset_dev_database() -> None:
    # Only reset dev environments (very important!)
    if "dev" not in os.environ.get("MESHDB_ENVIRONMENT", ""):
        logging.warn(f"Not resetting this environment. This environment is: \"{os.environ.get("MESHDB_ENVIRONMENT", "")}\"")
        return

    logging.info("Running database reset task")

    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        logging.error("Could not run backup. Missing AWS credentials!")
        return

    latest_backup = ""

    try:
        management.call_command("dbrestore", "-i", latest_backup)
    except Exception as e:
        logging.exception(e)
        raise e


@celery_app.task
def run_update_panoramas() -> None:
    logging.info("Running panorama sync task")
    try:
        sync_github_panoramas()
    except Exception as e:
        # Make sure the failure gets logged.
        logging.exception(e)
        raise e


@celery_app.task
def run_update_from_uisp() -> None:
    logging.info("Running UISP import & sync tasks")
    try:
        import_and_sync_uisp_devices(get_uisp_devices())
        import_and_sync_uisp_links(get_uisp_links())
        sync_link_table_into_los_objects()
    except Exception as e:
        # Make sure the failure gets logged.
        logging.exception(e)
        raise e


celery_app.conf.beat_schedule = {
    "update-panoramas-hourly": {
        "task": "meshapi.tasks.run_update_panoramas",
        "schedule": crontab(minute="0", hour="*/1"),
    },
    "import-from-uisp-hourly": {
        "task": "meshapi.tasks.run_update_panoramas",
        "schedule": crontab(minute="10", hour="*/1"),
    },
    "run-database-backup-hourly": {
        "task": "meshapi.tasks.run_database_backup",
        "schedule": crontab(minute="20", hour="*/1"),
    },
    "run-reset-dev-database-daily": {
        "task": "meshapi.tasks.run_database_backup",
        "schedule": crontab(minute="0", hour="0"),
    },
}
