#!/bin/bash

# ./Init_New_db.sh [db name] [username who will be set to owner] [pw for owner]
# Initialize FinTrackr db
# Admin should do this once, users never; can also be called by tests.
# createdb will fail if db already exists
# TODO pass the error out if creation fails
#
# Copyright (c) 2025 Stephanie Johnson

psql -d postgres -c "CREATE ROLE $2 WITH LOGIN PASSWORD '$3' CREATEDB CREATEROLE;"
createdb $1 -O $2
psql -d postgres -c "REVOKE CONNECT ON DATABASE $1 FROM PUBLIC;"
psql -d postgres -c "GRANT CONNECT ON DATABASE $1 TO $2;"
# Changed to using cur.copy_expert, so this line shouldn't be necessary anymore:
# psql -d postgres -c "GRANT pg_read_server_files TO $2 WITH ADMIN OPTION;"

PGPASSWORD=$3 psql -h localhost -d $1 -U $2 < src/fintrackr/schema.sql
  