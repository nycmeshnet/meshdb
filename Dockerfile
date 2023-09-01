FROM python:3.11-bullseye

WORKDIR /opt/meshdb

COPY pyproject.toml .
RUN mkdir meshdb
RUN pip install .

# FIXME: This probably isn't the file structure we want.
COPY . .

ENTRYPOINT gunicorn api:app --bind=0.0.0.0:8080