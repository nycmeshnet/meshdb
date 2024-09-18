#!/bin/bash

set -e

docker exec -i meshdb-postgres-1 psql -U meshdb < create_readonly_user.sql 
