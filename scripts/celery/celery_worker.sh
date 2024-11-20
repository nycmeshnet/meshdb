#!/bin/bash

celery -A meshdb worker -l INFO --uid $(id -u celery)
