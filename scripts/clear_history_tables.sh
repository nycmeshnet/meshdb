#!/bin/bash

DOCKER_PG_COMMAND="docker exec -i meshdb-postgres-1 psql -U meshdb -d meshdb"
tables=(
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
)

set -ex

for table_name in "${tables[@]}"
do
	echo "TRUNCATE ${table_name} CASCADE;" | $DOCKER_PG_COMMAND
done

