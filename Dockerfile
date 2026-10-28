# ---------- build stage ----------
FROM debian:trixie-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/

# git + ca-certificates are needed to fetch the git+https dependencies
RUN apt-get -y update && \
    apt-get -y install \
    ca-certificates \
    git

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed

WORKDIR /opt/meshdb

# Installs Python (from requires-python) and resolves/installs dependencies
COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# ---------- runtime stage ----------
FROM debian:trixie-slim

# netcat-openbsd is used to check if the db is available
# ca-certificates is needed for outbound HTTPS (S3, Datadog, geocoding, etc.)
RUN apt-get -y update && \
    apt-get -y install \
    ca-certificates \
    netcat-openbsd \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Same paths as the builder: the venv's python symlinks into /opt/python
COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /opt/meshdb

RUN useradd -ms /bin/bash celery # Celery does not recommend running as root

COPY ./scripts ./scripts

# Doing it like this should enable both dev and prod to work fine
COPY ./src/meshweb/static .

COPY ./src .

ENTRYPOINT ["sh", "-c", "./scripts/entrypoint.sh && exec gunicorn 'meshdb.wsgi' --workers 4 --timeout 120 --graceful-timeout 2 --bind=0.0.0.0:8081"]
