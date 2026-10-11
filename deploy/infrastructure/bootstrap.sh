#!/bin/sh
set -eu
cd "$(dirname "$0")"
umask 077
if [ ! -f .env ]; then
  command -v openssl >/dev/null
  printf 'POSTGRES_PASSWORD=%s\nREDIS_PASSWORD=%s\n' "$(openssl rand -hex 32)" "$(openssl rand -hex 32)" > .env
fi
chmod 600 .env
docker compose up -d --wait --wait-timeout 180
docker compose exec -T postgres psql -U welcome -d welcome -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS vector;'
docker compose ps
