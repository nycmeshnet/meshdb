#!/bin/bash

echo 'Waiting for Postgres'

echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT"

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
done

echo 'DB started'

# It's okay to start Celery in the background and continue without waiting, even though "migrate"
# might make DB changes we want to notify for since tasks are queued by Django Webhook and
# are executed as soon as celery starts
# FIXME: This makes testing locally a bit awkward, since this isn't started by "manage.py runserver"
#  maybe there's a way to do this better?
echo 'Starting Celery Worker...'
celery -A meshdb worker -l DEBUG -f /var/log/meshdb-celery.log &
celery -A meshdb beat -l DEBUG -f /var/log/meshdb-celery-beat.log -s /tmp/celerybeat-schedule &

echo 'Running Migrations...'
python manage.py makemigrations
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

