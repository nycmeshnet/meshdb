#!/bin/bash

DOCKER_PG_COMMAND="docker exec -i meshdb-postgres-1 psql -U meshdb -d meshdb"
DATA_DIR="./spreadsheet_data/"
tables=(
"meshapi_los"
"meshapi_link"
"meshapi_accesspoint"
"meshapi_sector"
"meshapi_device"
"meshapi_building_nodes"
"meshapi_node"
"meshapi_install"
"meshapi_building"
"meshapi_member"
"meshapi_historicallos"
"meshapi_historicallink"
"meshapi_historicalaccesspoint"
"meshapi_historicalsector"
"meshapi_historicaldevice"
"meshapi_historicalbuilding_nodes"
"meshapi_historicalnode"
"meshapi_historicalinstall"
"meshapi_historicalbuilding"
"meshapi_historicalmember"
)
set -ex

# Make sure our files exist.
if [ ! -d "$DATA_DIR" ]; then
	echo "$DATA_DIR missing!"
	exit 1
fi

for table_name in "${tables[@]}"
do
    if [ ! -e "spreadsheet_data/$table_name.sql" ]; then
		echo "$table_name.sql is missing!"
		exit 1
	fi
done

num_tables=${#tables[@]}

# Import the new data
for table_name in "${tables[@]}"
do
	cat "spreadsheet_data/$table_name.sql" | $DOCKER_PG_COMMAND
done

# Fix the auto numbering sequence for installs
max_install_number=$(($(${DOCKER_PG_COMMAND} -c "SELECT MAX(install_number) FROM meshapi_install" -At) + 1))
${DOCKER_PG_COMMAND} -c "ALTER SEQUENCE meshapi_install_install_number_seq RESTART WITH ${max_install_number}"
