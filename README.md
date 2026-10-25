# MeshDB

<p align="center">
  <img height="300px" src="https://github.com/andybaumgar/meshdb/assets/42927786/0f715a4e-99e3-402d-bc39-66f50eb0a94b" alt="MeshDB Logo">
</p>

## A Database for Tracking NYCMesh Member Installs

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Flotia%2Fmeshdb%2Frefs%2Fheads%2Fspecify-python-version-in-pyproject%2Fpyproject.toml)
[![Deployment Status](https://github.com/WillNilges/meshdb/actions/workflows/publish-and-deploy.yaml/badge.svg)](https://github.com/WillNilges/meshdb/actions/workflows/publish-and-deploy.yaml)
[![codecov](https://codecov.io/github/nycmeshnet/meshdb/graph/badge.svg?token=9PK9R0H6ZO)](https://codecov.io/github/nycmeshnet/meshdb)

We use `MeshDB` to track information about Buildings, Members, Installs, Nodes,
Devices, and Links; Any info we need in order to get hardware on a rooftop near you lives in here.

This project aims to provide a convenient, stable, and sane interface for use with
robots and humans. For more information, [check the
wiki](https://wiki.nycmesh.net/books/6-services-software/chapter/meshdb)

To start contributing, find a [good first issue](https://github.com/nycmeshnet/meshdb/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22).

## Setting up a Development Environment

### Requirements

#### Build tooling

[`uv`](https://docs.astral.sh/uv/) - [installation instructions](https://docs.astral.sh/uv/getting-started/installation/)

#### External services

- [PostgreSQL](https://www.postgresql.org/)
- [Pelias](https://pelias.io/)
- [Redis](https://redis.io)

We have a handy [docker-compose](docker-compose.yaml) file that allows you to set all the external services up with a single command. See
[Setting up the required external services](#setting-up-the-required-external-services)

> [!NOTE]
> In order to use docker compose you must have
> [docker](https://www.docker.com/products/docker-desktop/)
> or [podman](https://podman-desktop.io/) installed

### Fork Repo

Fork this repo.

> [!NOTE]
> If you cloned nycmeshnet/meshdb, you can change your origin by doing the following:
>
> ```console
> git remote remove origin
> git remote add origin https://github.com/<your_username>/meshdb
> git remote add upstream https://github.com/nycmeshnet/meshdb
> ```

### Development environment options

#### Dev Container

If you would like to develop in a [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers)

1. Make sure you have VS Code installed.
2. Install the Dev Containers extension: `ms-vscode-remote.remote-containers`
3. [Open the repo folder in the container](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-an-existing-folder-in-a-container).
4. Continue on the VS Code terminal (where your project is opened) follow normal developer setup.

#### Locally on your machine

> [!NOTE]
> If you are using NixOS, activate the dev environment with
> `nix-shell`, and then proceed with the below instructions.

Set up the project using `uv`. The `--all extras` option
ensures that all development packages are also installed

```console
uv sync --all extras
```

### Set Environment Variables

Next, copy the out the `.env.sample` file to `.env` and load it into
your environment.

```console
cp .env.sample .env
nano .env # Or your favorite text editor, fill in the blank variables
```

You're gonna need a `DJANGO_SECRET_KEY`, one is already provided in the
sample file, but if you want to generate your follow the directions
below.

### Generating `DJANGO_SECRET_KEY` (optional)

There's already a secret key for you in the .env.sample, but here's how
to generate a new one

```python
uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

> [!IMPORTANT]
> Make sure you're running in Debug mode if you want to see detailed traces.
> Set DEBUG=True in your `.env` file.

### Setting up the required external services

You will need the services identified in [External Services](#external-services)
which have been pre-defined in docker compose

```console
docker compose up -d postgres pelias redis
```

You *might* have to run the migrations. This will set up the DB for you.

```console
uv run python src/manage.py makemigrations
uv run python src/manage.py migrate
```

You'll probably want an admin account

```console
uv run python src/manage.py createsuperuser
```

And if you have access to a database export, you can use the
[scripts/import_datadump.sh](scripts/import_datadump.sh) script to populate
your database

> [!WARNING]
> This is *real member data*. DO NOT share this database with anyone
> under any circumstances.

```console
mkdir data/
cp <path_to_data_dump>/full_dump.sql data/
./scripts/import_datadump.sh
```

#### Advanced - MinIO for Local Dev

If you are going to use [minio](https://min.io/) for local S3 bucket emulation (not required for most tasks), also
start the minio related containers with `docker compose up -d minio createbuckets`. To have your local DB instance
use Minio, you will also need to set `S3_ENDPOINT="http://127.0.0.1:9000"` in your `.env` file.

> [!NOTE]
> You only need `createbuckets` once. It will initialize the bucket that MinIO talks to

#### Background Workers

If you want to do work with celery, you'll need to run a worker as well as a beat.
You can do this in two other terminals with these commands. `DEBUG` level is recommended
for the beat to see what beats are going to run

```console
uv run celery -A meshdb worker -l INFO
uv run celery -A meshdb beat -s /tmp/celerybeat-schedule -l DEBUG
```

You can also run the celery containers in docker containers with the
below command.

First copy your `.env` to `.env.container` and update the Redis and
Postgres URLs according to the comments in the file newly created
`.env.container` file.

```console
docker compose up -d celery-worker celery-beat
```

> [!NOTE]
> On Apple silicon macs, you may need to run the worker with the `--pool=solo` to avoid segfaults. i.e.
>
> ```console
> uv run celery -A meshdb worker -l INFO --pool=solo
> ```

### Accessing the server

Now you can get crackin'. Start up the development server

```console
uv run python src/manage.py runserver
```

Once the server is running should now be able to access the API:

```console
curl http://127.0.0.1:8000/api/v1/    # Should echo "We're Meshin" to indicate 200 status
```

### Running the Unit Tests

We use [pytest](https://docs.pytest.org/en/stable/) with the
[pytest-django](https://pytest-django.readthedocs.io/en/stable/) plugin

```console
uv run pytest
```

### Code Coverage

To view coverage add the `--cov` flag which will print per-file coverage
the the console.

```console
uv run pytest --cov
```

### Adding Tests

#### Unit Tests

Tests live in [src/meshapi/tests/](src/meshapi/tests/). It might make
sense to add your test to an existing file within that directory,
depending on what it's doing, or you can add a whole new file.
See the [django documentation](https://docs.djangoproject.com/en/4.2/topics/testing/overview/)
for details on how to write a test, or check the directory for examples.

#### Integration Tests

> [!WARNING]
> Don't run the integration tests against the production copy of MeshDB. These tests make fake
> objects and could pollute the real database.

Integration tests are defined in subdirectories within the
[integ-tests/](integ-tests/) directory.

They are automatically run by the deployment pipeline to prevent issues
from reaching our production stages. To run them locally, first edit
the `.env` file to set the `SITE_BASE_URL` environment variable to the
domain of the stage you want to run the tests against:

- `http://localhost:8000` to run them against a local copy of MeshDB (`manage.py runserver`)
- `https://devdb.nycmesh.net` to run them against the dev copy of MeshDB

You will also need a MeshDB API token which is appropriate for the stage you are running against,
set this via the `MESHDB_API_TOKEN` variable

Finally, run the integration tests with

```console
uv run pytest integ-tests
```

### Database Access

If you ever need to get into the database directly, it's easy to do so.

Get a shell on the postgres container:

```console
docker exec -it meshdb-postgres-1 bash
```

Switch to `postgres` user.

```console
su postgres
```

Run `psql`

```console
psql -U meshdb
```

### Cleaning up

When you're done, you can stop the server with `Ctrl+C`, and run
`docker compose down` to take down the containers.

> [!NOTE]
> To spin things back up again later, just run:
>
> ```console
> docker-compose up -d postgres pelias redis
> uv run python src/manage.py runserver
> ```

### Emulating the Production Environment

The production environment relies on Nginx and Gunicorn.

Clone the package with git and create the expected `.env` file (or
otherwise configure the environment variables specified in
`.env.sample` as appropriate to your environment).

```console
git clone https://github.com/andybaumgar/nycmesh-database
cp .env.sample .env
nano .env # Fill in any missing values
```

> [!NOTE]
> Check the above instructions if you need a `DJANGO_SECRET_KEY`

Finally, start the application and database servers using `docker compose`

```console
docker compose up
```

After a few minutes for image download & database setup, the development server
should be available at `127.0.0.1:8080`:

```console
# Should return "We're meshin'."
curl http://127.0.0.1:8080/api/v1
```

## Authentication (Permissions, Groups, and Tokens)

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
`PersonName-ApplicationName`. Grant the minimum necessary permissions directly on the user object using the admin UI.

Auth tokens can be created at `/admin/authtoken/tokenproxy/`.

To use them, you can include them as an HTTP header like so:

```console
curl -X GET http://127.0.0.1:8000/api/v1/members/ \
  -H 'Authorization:Token   <auth_token>'
```

### Admin Map

In `.env.sample`, the admin map frontend assets are configured to pull
from the production endpoint (map data will still be pulled from your
local database). If you wish to pull the admin map assets from a local
endpoint, host the map locally with:

```console
# In the map repo on the meshdb-admin branch
docker build -t meshdb-admin-map .
docker run -p "3000:3000" meshdb-admin-map
```

then edit the relevant `.env` variable to reflect the URL of the desired endpoint:

```console
ADMIN_MAP_BASE_URL=http://localhost:3000
```

### How to add environment variables

Follow [this PR](https://github.com/nycmeshnet/meshdb/pull/617/files)

### Making Data Exports for New Devs

To make importable data exports for new devs, first obtain a local copy of the data you want to share (see [Backups](#backups) below). Then:

Run the scramble script to obfuscate PII:

```console
uv run python src/manage.py scramble_members
```

Clear the data from the historical tables (so that we don't leak the data we just scrambled via a diff)

```console
scripts/clear_history_tables.sh
```

> [!WARNING]
> Be sure that you spot check the data to make sure the scramble process worked as expected.

Finally, create an importable datadump with:

```console
scripts/create_importable_datadump.sh
```

The file will be written to `data/full_dump.sql`, share this with the new devs

### Invoke Tasks

For convenience, this we use [Invoke](https://www.pyinvoke.org/) to wrap
common tasks into one-line commands. For example:

```console
uv run invoke format
```

Will automatically format the code, including sorting imports

You can also quickly peform all the relevant lint checks locally using

```console
uv run invoke lint
```

See [tasks.py](tasks.py) for a complete list of the tasks available

## Backups

> [!NOTE] For local backups set environment variable `LOCALBACKUP_FILE`
> to the path of the backup directory

### The Proper Way

We have a Celery job that runs hourly in production to back up to an S3 bucket.

To restore from a backup in production:

1. Get a shell in the meshdb container

    ```console
    docker exec -it meshdb-meshdb-1 bash
    ```

1. Find the backup you want to restore

    ```console
    uv run python manage.py listbackups

    Name                                     Datetime
    default-09855fadfa7e-2024-03-29-015116.psql.bin 03/29/24 01:51:16
    default-0c9b0a412baf-2024-03-31-170000.psql.bin 03/31/24 17:00:00
    default-12db99e5ec1d-2024-03-31-142422.psql.bin 03/31/24 14:24:22

    ...

    default-bd0acc253775-2024-03-31-163520.psql.bin 03/31/24 16:35:20
    ```

1. In a separate terminal, drop the old database

    ```console
    echo 'drop database meshdb; create database meshdb;' | docker exec -i meshdb-postgres-1 psql -U meshdb -d postgres
    ```

1. Restore the backup

   ```console
   uv run python manage.py dbrestore -i default-bd0acc253775-2024-03-31-163520.psql.bin --database default
   ```

### The Quick 'n Dirty Way

Export:

```console
docker exec -it meshdb-postgres-1 pg_dump -d meshdb -U meshdb >> Downloads/meshdb_dev.sql
```

Import:

```console
cat ~/Downloads/meshdb_dev.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
```
