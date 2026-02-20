#!/bin/bash
# Creates the agent_studio database in the shared Postgres instance.
# This runs automatically via docker-entrypoint-initdb.d on first container start.
# Uses SELECT to check existence first (CREATE DATABASE doesn't support IF NOT EXISTS).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE agent_studio'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agent_studio')\gexec
    GRANT ALL PRIVILEGES ON DATABASE agent_studio TO langfuse;

    SELECT 'CREATE DATABASE guardrails'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'guardrails')\gexec
    GRANT ALL PRIVILEGES ON DATABASE guardrails TO langfuse;
EOSQL

echo "[init-db] agent_studio + guardrails databases ready"
