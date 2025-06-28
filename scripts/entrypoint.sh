#!/bin/bash

echo 'MeshDB entrypoint.sh'

echo 'Waiting for Postgres'

echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT"

while ! nc -z $DB_HOST $DB_PORT; do
		sleep 0.1
        echo 'Trying again'
done

echo 'DB started'

echo 'Running Migrations...'
python manage.py makemigrations
python manage.py migrate

echo 'Collecting Static Files...'
python manage.py collectstatic --no-input

echo 'Creating Groups...'
python manage.py create_groups
