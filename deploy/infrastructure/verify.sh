#!/bin/sh
set -eu
cd "$(dirname "$0")"
token="$(openssl rand -hex 12)"
docker compose exec -T postgres psql -U welcome -d welcome -v ON_ERROR_STOP=1 -c "CREATE TABLE _deployment_smoke (value text NOT NULL); INSERT INTO _deployment_smoke VALUES ('$token');"
docker compose exec -T redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli SET welcome:deployment-smoke "$1"' sh "$token" >/dev/null
docker compose restart postgres redis >/dev/null
docker compose up -d --wait --wait-timeout 180 >/dev/null
actual="$(docker compose exec -T postgres psql -U welcome -d welcome -Atc 'SELECT value FROM _deployment_smoke;')"
[ "$actual" = "$token" ]
actual="$(docker compose exec -T redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli GET welcome:deployment-smoke')"
[ "$actual" = "$token" ]
docker compose exec -T postgres psql -U welcome -d welcome -Atc 'DROP TABLE _deployment_smoke;' >/dev/null
docker compose exec -T redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli DEL welcome:deployment-smoke' >/dev/null
extension="$(docker compose exec -T postgres psql -U welcome -d welcome -Atc "SELECT extversion FROM pg_extension WHERE extname='vector';")"
[ -n "$extension" ]
printf 'PASS: PostgreSQL and Redis persist data after restart; pgvector %s\n' "$extension"
