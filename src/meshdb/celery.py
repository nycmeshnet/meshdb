import os
from pathlib import Path
from celery import Celery, bootsteps
from celery.apps.worker import Worker
from celery.signals import beat_init, worker_ready, worker_shutdown
from datadog import initialize, statsd
from dotenv import load_dotenv
from django.conf import settings

HEARTBEAT_FILE = Path("/tmp/celery_worker_heartbeat")
READINESS_FILE = Path("/tmp/celery_worker_ready")
BEAT_READINESS_FILE = Path("/tmp/celery_beat_ready")


# This is still somewhat contentious in the Celery community, but the popular
# opinion seems to be this approach:
# https://medium.com/ambient-innovation/health-checks-for-celery-in-kubernetes-cf3274a3e106
# https://github.com/celery/celery/issues/4079#issuecomment-1270085680
# https://docs.celeryq.dev/projects/pytest-celery/en/latest/userguide/signals.html#signals-py
class LivenessProbe(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def __init__(self, parent: Worker, **kwargs: dict) -> None:
        self.requests: list = []
        self.tref = None

    def start(self, parent: Worker) -> None:
        self.tref = parent.timer.call_repeatedly(
            1.0,
            self.update_heartbeat_file,
            (parent,),
            priority=10,
        )

    def stop(self, parent: Worker) -> None:
        HEARTBEAT_FILE.unlink(missing_ok=True)

    def update_heartbeat_file(self, parent: Worker) -> None:
        statsd.increment("meshdb.celery.heartbeat")
        HEARTBEAT_FILE.touch()


@worker_ready.connect  # type: ignore[no-redef]
def worker_ready(**_: dict) -> None:
    READINESS_FILE.touch()


@worker_shutdown.connect  # type: ignore[no-redef]
def worker_shutdown(**_: dict) -> None:
    READINESS_FILE.unlink(missing_ok=True)


@beat_init.connect
def beat_ready(**_: dict) -> None:
    BEAT_READINESS_FILE.touch()


# Initialize dogstatsd
initialize(statsd_host="datadog-agent.datadog.svc.cluster.local", statsd_port=8125)

load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")

# Use the docker-hosted Redis container as the backend for Celery
app = Celery("meshdb", broker= settings.CELERY_BROKER)

app.steps["worker"].add(LivenessProbe)

# https://stackoverflow.com/questions/77479841/adding-celery-settings-what-does-it-do#78088996
app.conf.broker_connection_retry_on_startup = True

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
