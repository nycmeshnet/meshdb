FROM python:3.11-bullseye

RUN apt-get -y update; apt-get -y install netcat

WORKDIR /opt/meshdb

COPY pyproject.toml .
RUN mkdir meshdb
RUN pip install .

COPY entrypoint.sh .

COPY ./meshdb .

ENTRYPOINT ./entrypoint.sh && exec gunicorn 'meshdb.wsgi' --graceful-timeout 2 --bind=0.0.0.0:8081
