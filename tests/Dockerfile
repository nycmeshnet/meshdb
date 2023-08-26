FROM python:3.11-bullseye

WORKDIR /opt/meshdb_tests
COPY ./tests/requirements.txt .
RUN pip install -r requirements.txt

# FIXME: This probably isn't the file structure we want.
COPY . .

ENTRYPOINT PYTHONPATH=. pytest