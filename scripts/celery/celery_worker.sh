#!/bin/bash

celery -A meshdb worker -l DEBUG --uid $(id -u celery)
