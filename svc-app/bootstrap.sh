#!/bin/sh
set -e
DB_HOST_DIRECT="${POSTGRES_HOST_DIRECT:-db}"
DB_PORT_DIRECT="${POSTGRES_PORT_DIRECT:-5432}"
echo "Waiting for database..."
until pg_isready -h "$DB_HOST_DIRECT" -p "$DB_PORT_DIRECT" -U "$POSTGRES_USER"; do sleep 1; done
echo "Applying migrations..."
POSTGRES_HOST="$DB_HOST_DIRECT" POSTGRES_PORT="$DB_PORT_DIRECT" python manage.py migrate --noinput
echo "Seeding catalog (no-op if already populated)..."
POSTGRES_HOST="$DB_HOST_DIRECT" POSTGRES_PORT="$DB_PORT_DIRECT" python manage.py load_catalog --seed-if-empty
echo "Collecting static..."
python manage.py collectstatic --noinput --clear --verbosity 0
echo "Bootstrap done."
