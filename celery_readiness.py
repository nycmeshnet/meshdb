import sys
from pathlib import Path
READINESS_FILE = Path('/tmp/celery_worker_ready')

if not READINESS_FILE.is_file():
    sys.exit(1)

sys.exit(0)
