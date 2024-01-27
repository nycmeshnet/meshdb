#!/bin/bash

echo 'Waiting for Postgres'

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
done

echo 'DB started'

# It's okay to start Celery in the background and continue without waiting, even though "migrate"
# might make DB changes we want to notify for since tasks are queued by Django Webhook and
# are executed as soon as celery starts
echo 'Staring Celery Worker...'
celery -A meshdb worker -l INFO &

echo 'Running Migrations...'
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

