FROM python:3.11-bullseye

WORKDIR /opt/meshdb

COPY pyproject.toml .
RUN mkdir meshdb
RUN pip install .

# FIXME: This probably isn't the file structure we want.
COPY . .

ENTRYPOINT gunicorn 'meshdb:create_app()' --graceful-timeout 2 --bind=0.0.0.0:8080
