#!/bin/bash

DOCKER_PG_COMMAND="docker exec -i meshdb-postgres-1 pg_dump -U meshdb"
DATA_DIR="./data/"
tables=(
"meshapi_accesspoint"
"meshapi_building"
"meshapi_building_nodes"
"meshapi_device"
"meshapi_historicalaccesspoint"
"meshapi_historicalbuilding"
"meshapi_historicalbuilding_nodes"
"meshapi_historicaldevice"
"meshapi_historicalinstall"
"meshapi_historicallink"
"meshapi_historicallos"
"meshapi_historicalmember"
"meshapi_historicalnode"
"meshapi_historicalsector"
"meshapi_install"
"meshapi_link"
"meshapi_los"
"meshapi_member"
"meshapi_node"
"meshapi_sector"
)
set -ex

# Make sure our files exist.
if [ ! -d "$DATA_DIR" ]; then
	echo "$DATA_DIR missing!"
	exit 1
fi

docker exec -i meshdb-postgres-1 pg_dump -U meshdb -d meshdb ${tables[@]/#/-t } > "$DATA_DIR/full_dump.sql"

