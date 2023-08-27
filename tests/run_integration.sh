#!/bin/bash

set -e

podman build --tag meshdb_integration -f ./tests/Dockerfile .

podman run --rm --network meshdb_api --env-file=.env -it meshdb_integration:latest