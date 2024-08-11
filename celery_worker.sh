#!/bin/bash

celery -A meshdb worker -l DEBUG --uid 1069
