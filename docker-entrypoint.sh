#!/bin/sh
# Starts an embedded PostgreSQL when DATABASE_URL is not provided (single-container mode).
# On Railway, prefer attaching the managed PostgreSQL plugin: it sets DATABASE_URL and
# this block is skipped. Either way, mount a volume at /data so data survives redeploys.
set -e
mkdir -p "$UPLOAD_DIR"

if [ -z "$DATABASE_URL" ]; then
  PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | tail -1)
  if [ -z "$PG_BIN" ]; then
    echo "[entrypoint] DATABASE_URL is not set and this image has no embedded PostgreSQL (EMBEDDED_PG=0)." >&2
    exit 1
  fi
  mkdir -p "$PGDATA" /run/postgresql
  chown -R postgres:postgres "$PGDATA" /run/postgresql
  if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "[entrypoint] initialising embedded PostgreSQL in $PGDATA"
    gosu postgres "$PG_BIN/initdb" -D "$PGDATA" -U postgres --auth-local=trust --auth-host=scram-sha-256 -E UTF8 >/dev/null
  fi
  gosu postgres "$PG_BIN/pg_ctl" -D "$PGDATA" -o "-c listen_addresses='' -k /run/postgresql" -w start
  gosu postgres psql -h /run/postgresql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='pathouz'" | grep -q 1 \
    || gosu postgres createdb -h /run/postgresql -U postgres pathouz
  export DATABASE_URL="postgresql+asyncpg://postgres@/pathouz?host=/run/postgresql"
  trap 'gosu postgres "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast stop' TERM INT
fi

if [ -z "$JWT_SECRET" ]; then
  echo "[entrypoint] JWT_SECRET not set: using a generated secret kept in /data/.jwt_secret (mount a volume at /data so sessions survive redeploys)." >&2
fi

"$@" &
APP_PID=$!
wait "$APP_PID"
