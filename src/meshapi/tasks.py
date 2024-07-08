import os

from celery.schedules import crontab
from django.core import management

from meshapi.views.panoramas import sync_github_panoramas
from meshdb.celery import app as celery_app

import logging


@celery_app.task
def run_database_backup() -> None:
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
def run_update_panoramas() -> None:
    logging.info("Running panorama sync task")
    try:
        sync_github_panoramas()
    except Exception as e:
        # Make sure the failure gets logged.
        logging.exception(e)
        raise e


celery_app.conf.beat_schedule = {
    "run-database-backup-hourly": {
        "task": "meshapi.tasks.run_database_backup",
        "schedule": crontab(minute="0", hour="*/1"),
    },
    "update-panoramas-hourly": {
        "task": "meshapi.tasks.run_update_panoramas",
        "schedule": crontab(minute="0", hour="*/1"),
    },
}
