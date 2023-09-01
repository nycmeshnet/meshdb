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