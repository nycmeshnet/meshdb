#!/bin/bash

set -e

ct_cmd=podman

while getopts 'd' OPTION; do
    case "$OPTION" in
        d)
            ct_cmd=docker
            ;;
        ?)
            echo "Provide -d to run with docker, otherwise this script uses Podman."
            ;;
    esac
done

$ct_cmd build --tag meshdb_integration -f ./tests/Dockerfile .

$ct_cmd run --rm --network meshdb_api --env-file=.env -it meshdb_integration:latest