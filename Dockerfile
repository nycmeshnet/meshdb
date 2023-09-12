FROM python:3.11-bullseye

# For healthcheck
RUN apt-get -y update; apt-get -y install netcat

WORKDIR /opt/meshdb

COPY pyproject.toml .
RUN mkdir src
RUN pip install .

COPY entrypoint.sh .

COPY ./src .

ENTRYPOINT ./entrypoint.sh && exec gunicorn 'meshdb.wsgi' --graceful-timeout 2 --bind=0.0.0.0:8081
