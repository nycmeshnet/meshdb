#!/bin/bash

ENV_NAME="$1"
EXPECTED_KEYFILE_NAME="./meshdb$ENV_NAME"

if [ ! -f "$EXPECTED_KEYFILE_NAME" ]; then
    ssh-keygen -t ed25519 -f $EXPECTED_KEYFILE_NAME -C meshdb${ENV_NAME}@db.mesh.nycmesh.net -q -N ""
else
    echo "File $EXPECTED_KEYFILE_NAME already exists"
fi
