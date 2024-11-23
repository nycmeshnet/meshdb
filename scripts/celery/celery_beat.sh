#!/bin/bash

celery -A meshdb beat -l INFO -s /tmp/celerybeat-schedule --pidfile=/tmp/celery-beat.pid
