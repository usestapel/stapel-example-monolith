#!/bin/sh
set -eu

ensure_database_exists() {
    database=$1
    if psql -v ON_ERROR_STOP=1 -d postgres --username "$POSTGRES_USER" -lqt \
        | cut -d '|' -f 1 | grep -qw "$database"; then
        echo "  database '$database' exists"
    else
        echo "  creating database '$database'"
        psql -v ON_ERROR_STOP=1 -d postgres --username "$POSTGRES_USER" <<-EOSQL
            CREATE DATABASE $database;
            GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
    fi
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "Ensuring databases exist: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
        db=$(echo "$db" | xargs)
        [ -n "$db" ] && ensure_database_exists "$db"
    done
fi
