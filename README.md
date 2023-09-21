# meshdb

## A Database for Tracking NYCMesh Member Installs

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg?logo=python)](https://www.python.org/downloads/release/python-3115/)
[![Django Rest Framework](https://img.shields.io/badge/django-rest_framework-red)](https://www.django-rest-framework.org/)
[![Nginx](https://img.shields.io/badge/nginx-green?logo=nginx)](https://hub.docker.com/_/nginx)
[![Runs on Docker](https://img.shields.io/badge/runs_on-Docker-blue?logo=docker)](https://docs.docker.com/compose/)

Welcome to the `nth` attempt at making an API! This was started out of hatred
for the **New Node Form**.

We use `meshdb` (that's how you should refer to it) to track information about
Buildings, Members, Installs, and Requests; Any info we need in order to get
hardware on a rooftop near you lives in here.

This project aims to provide a convenient, stable, and sane API for use with
robots and humans. For more information, [check the
wiki](http://wiki.mesh.nycmesh.net/books/software-services/page/meshdb)

## Setup

### Dev Environment

The production environment relies on Nginx and Gunicorn, but for development,
you can use Django's tools. You'll also need Python 3.11, and pip, of course.

For safety, create a venv

```
python -m venv venv
source .venv/bin/activate
```

Then, install dependencies

```
pip install '.[dev]'
```

Next, fill out the `.env.sample` file and load it into your environment.

You're gonna need a `DJANGO_SECRET_KEY`:

### Generating `DJANGO_SECRET_KEY`

There's already a secret key for you in the .env.sample, but if you need another one...

```python
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

> [!IMPORTANT]
> Make sure you're running in Debug mode if you want to see detailed traces.
> Set DEBUG=True in your `.env` file.

If you have a database, great, go nuts. If you don't, you can use
`docker-compose`.

> [!WARNING]
> If you have an old build, you might have to re-build the container
> by adding `--build` to the below command.

```sh
docker-compose up postgres
```

You might have to run the migrations. This will set up the DB for you.

```sh
python manage.py makemigrations
python manage.py migrate
```

You'll probably want an admin account
```
python ./src/manage.py createsuperuser
```

Then, you can get crackin'

```sh
python manage.py runserver
```

### Prod Environment

Clone the package with git and create the expected `.env` file (or otherwise
configure the environment variables specified in `.env.sample` as appropriate
to your environment).

```sh 
git clone https://github.com/andybaumgar/nycmesh-database
cp .env.sample .env
nano .env # Fill in any missing values
```

> [!NOTE]
> Check the above instructions if you need a `DJANGO_SECRET_KEY`

Finally, start the application and database servers using `docker compose`

```sh
docker compose up
```

After a few minutes for image download & database setup, the development server
should be available at `127.0.0.1:8080`: 

```sh
# Should return "We're meshin'."
curl http://127.0.0.1:8080/api/v1
```

## Unit Tests 

To run the unit tests, first create a virtual env in the project root 

```sh
python3 -m venv .venv source .venv/bin/activate
```

Next, install the project dependencies, including dev dependencies
```sh
pip install -e ".[dev]"
```

Finally, run `pytest`:
```sh
pytest
```

## Invoke.py Commands

For convenience, this package uses [invoke](https://www.pyinvoke.org/) to wrap
common tasks into one-line commands. For example:

```sh
invoke format
```

Will automatically apply `black` formatting and `isort` import sorting in a
single command.

You can also quickly peform all the relevant lint checks locally using 
```sh
invoke lint
```

See `tasks.py` for a complete list of the tasks available.

