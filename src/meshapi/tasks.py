import logging
import os

from celery.schedules import crontab
from django.core import management
from flags.state import disable_flag, enable_flag

from meshapi.util.django_flag_decorator import skip_if_flag_disabled
from meshapi.util.panoramas import sync_github_panoramas
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links
from meshapi.util.uisp_import.sync_handlers import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)
from meshdb.celery import app as celery_app
from meshdb.settings import MESHDB_ENVIRONMENT


@celery_app.task
@skip_if_flag_disabled("TASK_ENABLED_RUN_DATABASE_BACKUP")
def run_database_backup() -> None:
    # Don't run a backup unless it's prod
    if MESHDB_ENVIRONMENT != "prod2":
        raise EnvironmentError(f'Not running database backup. This environment is: "{MESHDB_ENVIRONMENT}"')

    logging.info(f'Running database backup task. This environment is "{MESHDB_ENVIRONMENT}"')
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        raise ValueError("Could not run backup. Missing AWS credentials!")

    try:
        management.call_command("dbbackup")
    except Exception as e:
        logging.exception(e)
        raise e


@celery_app.task
@skip_if_flag_disabled("TASK_ENABLED_RESET_DEV_DATABASE")
def reset_dev_database() -> None:
    # Only reset dev environments (very important!)
    if "dev" not in MESHDB_ENVIRONMENT:
        raise EnvironmentError(f'Not resetting this database. This environment is: "{MESHDB_ENVIRONMENT}"')

    logging.info(f'Running database reset task. This environment is: "{MESHDB_ENVIRONMENT}"')

    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        raise ValueError("Could not run database reset. Missing AWS credentials!")

    try:
        enable_flag("MAINTENANCE_MODE")
        management.call_command("dbrestore", "--noinput", "--database", "default")
        management.call_command("scramble_members", "--noinput")
        disable_flag("MAINTENANCE_MODE")
    except Exception as e:
        logging.exception(e)
        raise e


@celery_app.task
@skip_if_flag_disabled("TASK_ENABLED_UPDATE_PANORAMAS")
def run_update_panoramas() -> None:
    logging.info("Running panorama sync task")
    try:
        panoramas_saved, warnings = sync_github_panoramas()
        logging.info(f"Saved {panoramas_saved} panoramas. Got {len(warnings)} warnings.")
        logging.warning(f"warnings:\n{warnings}")
    except Exception as e:
        # Make sure the failure gets logged.
        logging.exception(e)
        raise e


@celery_app.task
@skip_if_flag_disabled("TASK_ENABLED_SYNC_WITH_UISP")
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


jitter_minutes = 0 if MESHDB_ENVIRONMENT == "prod2" else 2

celery_app.conf.beat_schedule = {
    "update-panoramas-hourly": {
        "task": "meshapi.tasks.run_update_panoramas",
        "schedule": crontab(minute=str(jitter_minutes), hour="*/1"),
    },
    "import-from-uisp-hourly": {
        "task": "meshapi.tasks.run_update_from_uisp",
        "schedule": crontab(minute=str(jitter_minutes + 10), hour="*/1"),
    },
}

if MESHDB_ENVIRONMENT == "prod2":
    celery_app.conf.beat_schedule["run-database-backup-hourly"] = {
        "task": "meshapi.tasks.run_database_backup",
        "schedule": crontab(minute="20", hour="*/1"),
    }

if MESHDB_ENVIRONMENT == "dev3":
    celery_app.conf.beat_schedule["run-reset-dev-database-daily"] = {
        "task": "meshapi.tasks.run_database_backup",
        "schedule": crontab(minute="30", hour="0"),
    }
