#!/bin/bash

celery -A meshdb beat -l DEBUG -s /tmp/celerybeat-schedule
