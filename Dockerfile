FROM python:3.11-bullseye

WORKDIR /opt/meshdb

# FIXME: This probably isn't the file structure we want.
COPY . .
RUN pip install .

ENTRYPOINT gunicorn api:app --bind=0.0.0.0:8080