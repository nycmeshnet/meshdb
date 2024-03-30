FROM python:3.11-bookworm

# For healthcheck
RUN apt-get -y update; apt-get -y install netcat-openbsd postgresql-client-15

WORKDIR /opt/meshdb

COPY pyproject.toml .
RUN mkdir src
RUN pip install .

COPY entrypoint.sh .

# Doing it like this should enable both dev and prod to work fine
COPY ./src/meshweb/static .

COPY ./src .

ENTRYPOINT ./entrypoint.sh && exec gunicorn 'meshdb.wsgi' --graceful-timeout 2 --bind=0.0.0.0:8081 --log-file /var/log/gunicorn.log
