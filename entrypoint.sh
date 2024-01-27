#!/bin/bash

echo 'Waiting for Postgres'

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
done

echo 'DB started'

# It's okay to start Celery in the background and continue without waiting, even though "migrate"
# might make DB changes we want to notify for since tasks are queued by Django Webhook and
# are executed as soon as celery starts
# FIXME: This makes testing locally a bit awkward, since this isn't started by "manage.py runserver"
#  maybe there's a way to do this better?
echo 'Staring Celery Worker...'
celery -A meshdb worker -l INFO --detach

echo 'Running Migrations...'
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

