#!/bin/bash

PGHOST="127.0.0.1"
PGPASSWORD="abcd1234" # .env.example password
DATA_DIR="./spreadsheet_data/"

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

tables=("meshapi_member" "meshapi_building" "meshapi_install" "meshapi_link" "meshapi_sector")

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
	docker exec -i meshdb-postgres-1 psql -U meshdb -c "DROP TABLE IF EXISTS ${tables[i]}"
done

# Import the new data
for table_name in "${tables[@]}"
do
	cat "spreadsheet_data/$table_name.sql" | docker exec -i meshdb-postgres-1 psql -U meshdb
done

# Fix the numbering
for table_name in "${tables[@]}"
do
    if [[ "$table_name" == "meshapi_install" ]]; then
        max_id=$(($(docker exec -i meshdb-postgres-1 psql -U meshdb -c "SELECT MAX(install_number) FROM $table_name" -At) + 1))
        docker exec -i meshdb-postgres-1 psql -U meshdb -c "ALTER SEQUENCE "$table_name"_install_number_seq RESTART WITH $max_id"
    else
        max_id=$(($(docker exec -i meshdb-postgres-1 psql -U meshdb -c "SELECT MAX(id) FROM $table_name" -At) + 1))
        docker exec -i meshdb-postgres-1 psql -U meshdb -c "ALTER SEQUENCE "$table_name"_id_seq RESTART WITH $max_id"
    fi
done



