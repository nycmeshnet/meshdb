# meshdb

<p align="center">
  <img height="300px" src="https://github.com/andybaumgar/meshdb/assets/42927786/0f715a4e-99e3-402d-bc39-66f50eb0a94b" alt="MeshDB Logo">
</p>

## A Database for Tracking NYCMesh Member Installs

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg?logo=python)](https://www.python.org/downloads/release/python-3115/)

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
python --version # Make sure this is python 3.11.x before continuing
python -m venv .venv
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
> You will need to remove the traefik config from the network block.

```sh
docker-compose up -d postgres pelias redis
```

You might have to run the migrations. This will set up the DB for you.

```sh
python src/manage.py makemigrations
python src/manage.py migrate
```

You'll probably want an admin account
```
python src/manage.py createsuperuser
```

Then, you can get crackin'

```sh
python src/manage.py runserver
```

You should now be able to access the API:
```sh
curl http://127.0.0.1:8000/api/v1/    # Should echo "We're Meshin" to indicate 200 status
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

### Auth Tokens

We have very simple permission levels.

- **Unauthenticated**: A user using a route without authenticating
- **Installer**: Can view all fields, provision NNs, and edit installs
- **Admin**: Full access

We use Django Rest Framework's basic Auth Token implementation. To add a token,
you need a user, which can be created at `/admin/auth/user/`.

To determine what permissions the user has, add them to one of the pre-existing groups.

(Superuser and Staff are DRF-specific and should be restricted to people maintaining
the instance)

Auth tokens can be created at `/admin/authtoken/tokenproxy/`.

To use them, you can include them as an HTTP header like so:
```
curl -X GET http://127.0.0.1:8000/api/v1/members/ -H 'Authorization: Token <auth_token>'
```

## Unit Tests 

We use django's testing framework, based on `unittest`

To run the unit tests, first create a virtual environment and install the dependencies as specified 
under [Dev Environment](#dev-environment) above

Django's tests should spin up and tear down a mock database for us, but it's
still going to need somewhere to put that database, so go ahead and boot up the
one in your `docker-compose.yaml`

```sh
docker compose up -d postgres
```

Finally, run the tests:
```sh
python src/manage.py test meshapi
```

### Code Coverage

We'd like to cover as much of the code as is reasonable, and to see what we hit,
we use `coverage.py` as suggested by Django.

To run coverage, set up your venv, then wrap the testing command like so:

```sh
coverage run --source='.' src/manage.py test meshapi
```

To see the report, 

```sh
coverage report
```

## Adding Tests 

Tests live in `src/meshapi/tests/`. It might make sense to add your test to
an existing file within that directory, depending on what it's doing, or you
can add a whole new file. See the [django documentation](https://docs.djangoproject.com/en/4.2/topics/testing/overview/)
for details on how to write a test, or check the directory for examples.

## Database

If you ever need to get into the database directly, it's easy to do so.

Get a shell on the postgres container:

```sh
docker exec -it meshdb-postgres-1 bash
```

Switch to `postgres` user.

```sh
su postgres
```

Run `psql`

```sh
psql -U meshdb
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

