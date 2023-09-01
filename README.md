# meshdb

## The Premiere NYCMesh Member/Install Database

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

Finally, open another window, and run the tests.

`PYTHONPATH=. pytest .`


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