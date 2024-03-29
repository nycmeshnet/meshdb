import os

from celery.schedules import crontab
from django.core import management

from meshapi.views.panoramas import sync_github_panoramas
from meshdb.celery import app as celery_app


@celery_app.task
def run_database_backup():
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        print("Could not run backup. Missing AWS credentials!")
        return

    management.call_command("dbbackup")


@celery_app.task
def run_update_panoramas():
    sync_github_panoramas()


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
