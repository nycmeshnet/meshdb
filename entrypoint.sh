#!/bin/bash

echo 'Waiting for Postgres'

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
done

echo 'DB started'

echo 'Running Migrations...'
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

