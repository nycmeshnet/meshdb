# MeshDB

<p align="center">
  <img height="300px" src="https://github.com/andybaumgar/meshdb/assets/42927786/0f715a4e-99e3-402d-bc39-66f50eb0a94b" alt="MeshDB Logo">
</p>

## A Database for Tracking NYCMesh Member Installs

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg?logo=python)](https://www.python.org/downloads/release/python-3115/)
[![Deployment Status](https://github.com/WillNilges/meshdb/actions/workflows/publish-and-deploy.yaml/badge.svg)](https://github.com/WillNilges/meshdb/actions/workflows/publish-and-deploy.yaml)


We use `MeshDB` to track information about Buildings, Members, Installs, Nodes, 
Devices, and Links; Any info we need in order to get hardware on a rooftop near you lives in here.

This project aims to provide a convenient, stable, and sane interface for use with
robots and humans. For more information, [check the
wiki](https://wiki.mesh.nycmesh.net/books/6-services-software/chapter/meshdb)

## Setup

### Dev Environment

The production environment relies on Nginx and Gunicorn, but for development,
you can use Django's tools. You'll also need Python 3.11, and pip, of course.

Firstly, fork this repo.

> [!NOTE]
> If you cloned nycmeshnet/meshdb, you can change your origin by doing the following:
> ```
> git remote remove origin
> git remote add origin https://github.com/<your_username>/meshdb
> git remote add upstream https://github.com/nycmeshnet/meshdb
> ```

#### Dev Container

If you would like to develop in a [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers)

1. Make sure you have VS Code installed.
2. Install the Dev Containers extension: `ms-vscode-remote.remote-containers`
3. [Open the repo folder in the container](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-an-existing-folder-in-a-container).
4. In a different shell, outside of VS Code, start the other containers: `docker compose up -d postgres pelias redis` (as below).
5. Continue on the VS Code terminal (where your project is opened) follow normal developer setup.

#### Host

If you are not using a Dev Container, for safety, create a venv

```
python --version # Make sure this is python 3.11.x before continuing
python -m venv .venv
source .venv/bin/activate
```

Then, install dependencies.

```
pip install -e '.[dev]'
```

### Set Environment Variables

Next, fill out the `.env.sample` file and load it into your environment.

```
cp .env.sample .env
nano .env # Or your favorite text editor, fill in the blank variables
```
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

And if you have access to it, you can use `import_spreadsheet_dump.sh` to populate
your database.

> [!WARNING]
> This is _real member data_. DO NOT share this database with anyone under any
> circumstances.

```sh
cp -R <path_to_data_dump> ./spreadsheet_data/
./import_spreadsheet_dump.sh
```

If you want to do work with celery, you'll need to run a worker as well as a beat.
You can do this in two other terminals with these commands. `DEBUG` level is recommended
for the beat to see what beats are going to run

```
celery -A meshdb worker -l INFO
celery -A meshdb beat -s /tmp/celerybeat-schedule -l DEBUG
```

Then, you can get crackin'

```sh
python src/manage.py runserver
```

You should now be able to access the API:
```sh
curl http://127.0.0.1:8000/api/v1/    # Should echo "We're Meshin" to indicate 200 status
```

When you're done, you can stop the server with `Ctrl+C`, and run `docker compose down` to take down the containers.

> [!NOTE]
> To spin things back up again later, just run:
> ```sh
> source .venv/bin/activate
> docker-compose up -d postgres pelias redis
> python src/manage.py runserver
> ```

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

### Authentication (Permissions, Groups, and Tokens)

We have very simple permission levels.

- **Unauthenticated**: A user using a route without authenticating
- **Installer**: Can view all fields, provision NNs, and edit installs
- **Admin**: Full access

We use Django Rest Framework's basic Auth Token implementation. To add a token,
you need a user, which can be created at `/admin/auth/user/`.

To determine what permissions the user has, add them to one of the pre-existing groups.

(Superuser and Staff are DRF-specific and should be restricted to people maintaining
the instance)

For software apps, create a new users for each application with the format 
`PersonName-ApplicationName`. Grant the minimum neccessary permissions directly on the user
object using the admin UI.

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
docker compose up -d postgres pelias redis
```

Finally, run the tests:
```sh
python src/manage.py test meshapi meshapi_hooks
```

### Code Coverage

We'd like to cover as much of the code as is reasonable, and to see what we hit,
we use `coverage.py` as suggested by Django.

To run coverage, set up your venv, then wrap the testing command like so:

```sh
coverage run --source='.' src/manage.py test meshapi meshapi_hooks
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

## Admin Map
In `.env.sample`, the admin map frontend assets are configured to pull from the production endpoint.
(map data will still be pulled from your local database). If you wish to pull the admin map assets 
from a local endpoint, host the map locally with:
```sh
# In the map repo on the meshdb-admin branch
docker build -t meshdb-admin-map .
docker run -p "3000:3000" meshdb-admin-map
```

then edit the relevant `.env` variable to reflect the URL of the desired endpoint:
```sh
ADMIN_MAP_BASE_URL=http://localhost:3000
```

### Backups

**The Proper Way**

We have a Celery job that runs hourly in production to back up to an S3 bucket.

To restore from a backup in production:

1. Get a shell in the meshdb container
```
$ docker exec -it meshdb-meshdb-1 bash
```

2. Find the backup you want to restore
```
root@eefdc57a46c2:/opt/meshdb# python manage.py listbackups
Name                                     Datetime
default-09855fadfa7e-2024-03-29-015116.psql.bin 03/29/24 01:51:16
default-0c9b0a412baf-2024-03-31-170000.psql.bin 03/31/24 17:00:00
default-12db99e5ec1d-2024-03-31-142422.psql.bin 03/31/24 14:24:22

...

default-bd0acc253775-2024-03-31-163520.psql.bin 03/31/24 16:35:20
```

3. In a separate terminal, drop the old database
```
$ echo 'drop database meshdb; create database meshdb;' | docker exec -i meshdb-postgres-1 psql -U meshdb -d postgres
```

4. Restore the backup
```
root@eefdc57a46c2:/opt/meshdb# python manage.py dbrestore -i default-bd0acc253775-2024-03-31-163520.psql.bin   
```

**The Quick 'n Dirty Way**

Export:

```
docker exec -it meshdb-postgres-1 pg_dump -d meshdb -U meshdb >> Downloads/meshdb_dev.sql
```

Import:

```
cat ~/Downloads/meshdb_dev.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
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

