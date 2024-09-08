#!/bin/bash

DOCKER_PG_COMMAND="docker exec -i meshdb-postgres-1 psql -U meshdb"
DATA_DIR="./spreadsheet_data/"
tables=("meshapi_link" "meshapi_accesspoint" "meshapi_sector" "meshapi_device" "meshapi_building_nodes" "meshapi_node" "meshapi_install" "meshapi_building" "meshapi_member")
#tables=("meshapi_link" "meshapi_building_nodes"  "meshapi_sector" "meshapi_device" "meshapi_install" "meshapi_member"  "meshapi_building" "meshapi_node")
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

# Don't need to create them.
# XXX (willnilges): Do we want to have an option to dump the tables?
#for table_name in "${tables[@]}"
#do
#    docker exec -i meshdb_postgres_1 pg_dump -U meshdb --table="$table_name" > "$table_name.sql"
#done

num_tables=${#tables[@]}

# Yeet
# XXX (willnilges): Would it be better to use manage.py?
for ((i = num_tables - 1; i >= 0; i--));
do
	$DOCKER_PG_COMMAND -c "DROP TABLE IF EXISTS ${tables[i]} CASCADE"
done

# Import the new data
for table_name in "${tables[@]}"
do
	cat "spreadsheet_data/$table_name.sql" | $DOCKER_PG_COMMAND
done

# Fix the auto numbering sequence for installs
max_install_number=$(($($DOCKER_PG_COMMAND -c "SELECT MAX(install_number) FROM $table_name" -At) + 1))
$DOCKER_PG_COMMAND -c "ALTER SEQUENCE "$table_name"_install_number_seq RESTART WITH $max_install_number"




