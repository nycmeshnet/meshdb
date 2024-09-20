#!/bin/bash

echo 'Waiting for Postgres'

echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT"

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
done

echo 'DB started'

echo 'Running Migrations...'
python manage.py makemigrations
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

echo 'Creating Groups...'
python maange.py create_groups
