#!/bin/bash

ddtrace-run celery -A meshdb worker -l DEBUG --uid $(id -u celery)
