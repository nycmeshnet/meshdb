# meshdb

## A Database for Tracking NYCMesh Member Installs

Welcome to the `nth` attempt at making an API! This was started out of hatred for our current solution for tracking installs/buildings/requests, the **New Node Form**.

This project aims to provide a convenient, stable, and sane API for use with robots and humans. 
For more information, [check the wiki](http://wiki.mesh.nycmesh.net/books/software-services/page/meshdb)

## Setup

To run a local copy from source code, first clone the package with git and create the expected
`.env` file (or otherwise configure the environment variables specified in `.env.sample` as 
appropriate to your environment).
```sh
git clone https://github.com/andybaumgar/nycmesh-database

cp .env.sample .env
nano .env # Fill in any missing values
```

### Generating secret keys for .env
 - `SECRET_KEY` can be generated with `python -c "import secrets; print(secrets.token_urlsafe())"`
 - `SECURITY_PASSWORD_SALT` can be generated with `python -c "import secrets; print(secrets.SystemRandom().getrandbits(128))"`

Finally, start the application and database servers using `docker compose`
```sh
docker compose up
```

After a few minutes for image download & database setup, the development server should be 
available at `127.0.0.1:8080`:
```sh
# Should return "[]" since the database is empty
curl http://127.0.0.1:8080/getMembers
```


## Unit Tests
To run the unit tests, first create a virtual env in the project root
```sh
python3 -m venv .venv
source .venv/bin/activate
```

Next, install the project dependencies, including dev dependencies
```sh
pip install -e ".[dev]"
```

Finally, run `pytest`:
```
pytest
```

## Integration Tests

If you want to continuously develop and test things, you probably want to have your IDE and debugger attached directly to the process that is running, which can be a little tricky in a container. Fortunately, `venv`s exist, so we can get around this problem pretty easily.

First, set up the database, as before, but _just_ the database.

`docker-compose up postgres`

In another window, setup a `venv`

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then, in a separate window, or in your IDE, you can run the meshdb server

`flask run --port 8080`

Copy the `.env.sample` file to `.env`, fill it out (prepend `export` for baremetal tests), and export it:

`source .env`

Finally, open another window, and run the tests.

`PYTHONPATH=. pytest .`

## Testing with `act`

You can use [`act`](https://github.com/nektos/act) to run our GitHub actions locally, if you want.

We have a Dockerfile you can borrow for that:
```
FROM ubuntu

RUN apt-get -y update; apt-get -y install python3.11-venv python3-pip
```

Build it: `docker build --tag=willnilges/act-ubuntu-latest .`

Because act [does not currently have `services` support](https://github.com/nektos/act/issues/173), you need to use the `docker-compose.yaml` to run a Postgres database for our integration tests separately.
```
docker-compose up postgres
```

Run the actions like this:
```
act --pull=false -P ubuntu-latest=willnilges/act-ubuntu-latest:latest --container-options "--network meshdb_api"
```

Optionally you can add a flag to choose which action to run: `-W .github/workflows/integration.yaml`


## Invoke.py Commands

For convenience, this package uses [invoke](https://www.pyinvoke.org/) to wrap common
tasks into one-line commands. For example:

```sh
invoke format
```

Will automatically apply `black` formatting and `isort` import sorting in a single command.

You can also quickly peform all the relevant lint checks locally using
```sh
invoke lint
```

See `tasks.py` for a complete list of the tasks available.

## Dependencies

This package uses [flask-security-too](https://flask-security-too.readthedocs.io/en/stable/) instead of flask-security. 
Ensure that the coorect docs are being used for development.
