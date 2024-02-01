python src/manage.py flush 
cat ./output_data/meshapi_building.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
cat ./output_data/meshapi_member.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
cat ./output_data/meshapi_install.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
cat ./output_data/meshapi_link.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
cat ./output_data/meshapi_sector.sql | docker exec -i meshdb-postgres-1 psql -U meshdb
