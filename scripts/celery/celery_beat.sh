#!/bin/bash

celery -A meshdb beat -l DEBUG -s /tmp/celerybeat-schedule --pidfile=/tmp/celery-beat.pid