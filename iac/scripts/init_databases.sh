#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Postgres init hook (runs once, on first volume creation, via
# /docker-entrypoint-initdb.d). Creates the dedicated Airflow role + database
# alongside the main `homepedia` DB. Idempotent-ish: guarded by IF NOT EXISTS.
#
# Env (provided by the postgres service): POSTGRES_USER, POSTGRES_DB,
# AIRFLOW_DB, AIRFLOW_DB_USER, AIRFLOW_DB_PASSWORD.
# -----------------------------------------------------------------------------
set -euo pipefail

AIRFLOW_DB="${AIRFLOW_DB:-airflow}"
AIRFLOW_DB_USER="${AIRFLOW_DB_USER:-airflow}"
AIRFLOW_DB_PASSWORD="${AIRFLOW_DB_PASSWORD:-airflow}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${AIRFLOW_DB_USER}') THEN
            CREATE ROLE ${AIRFLOW_DB_USER} LOGIN PASSWORD '${AIRFLOW_DB_PASSWORD}';
        END IF;
    END
    \$\$;
SQL

# CREATE DATABASE cannot run inside a DO/transaction block, so gate it separately.
if ! psql -tAc "SELECT 1 FROM pg_database WHERE datname = '${AIRFLOW_DB}'" \
        --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" | grep -q 1; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        -c "CREATE DATABASE ${AIRFLOW_DB} OWNER ${AIRFLOW_DB_USER};"
fi

echo "init_databases: '${AIRFLOW_DB}' DB and '${AIRFLOW_DB_USER}' role ready."
