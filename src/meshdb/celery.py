import os
from pathlib import Path

from celery import Celery, bootsteps
from celery.signals import beat_init, worker_ready, worker_shutdown
from dotenv import load_dotenv

HEARTBEAT_FILE = Path("/tmp/celery_worker_heartbeat")
READINESS_FILE = Path("/tmp/celery_worker_ready")
BEAT_READINESS_FILE = Path("/tmp/celery_beat_ready")


class LivenessProbe(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def __init__(self, worker, **kwargs):  # type: ignore[no-untyped-def]
        self.requests = []
        self.tref = None

    def start(self, worker):  # type: ignore[no-untyped-def]
        self.tref = worker.timer.call_repeatedly(
            1.0,
            self.update_heartbeat_file,
            (worker,),
            priority=10,
        )

    def stop(self, worker):  # type: ignore[no-untyped-def]
        HEARTBEAT_FILE.unlink(missing_ok=True)

    def update_heartbeat_file(self, worker):  # type: ignore[no-untyped-def]
        HEARTBEAT_FILE.touch()


@worker_ready.connect  # type: ignore[no-redef]
def worker_ready(**_):  # type: ignore[no-untyped-def]
    READINESS_FILE.touch()


@worker_shutdown.connect  # type: ignore[no-redef]
def worker_shutdown(**_):  # type: ignore[no-untyped-def]
    READINESS_FILE.unlink(missing_ok=True)


@beat_init.connect
def beat_ready(**_):  # type: ignore[no-untyped-def]
    BEAT_READINESS_FILE.touch()


load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")

# Use the docker-hosted Redis container as the backend for Celery
app = Celery("meshdb", broker=os.environ.get("CELERY_BROKER", "redis://localhost:6379/0"))

app.steps["worker"].add(LivenessProbe)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
