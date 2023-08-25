FROM python:3.11-bullseye

WORKDIR /opt/meshdb
COPY requirements.txt .
RUN pip install -r requirements.txt

# FIXME: This probably isn't the file structure we want.
COPY . .

ENTRYPOINT gunicorn api:app --bind=0.0.0.0:8080