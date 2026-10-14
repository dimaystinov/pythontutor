#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/setup.py
docker info > /dev/null
if [ "${EXECUTION_MODE:-browser}" = "server" ] || grep -q '^EXECUTION_MODE=server$' .env 2>/dev/null; then
    docker build -f runner/Dockerfile.worker -t pythontutor-worker:local .
    export COMPOSE_PROFILES=server
fi
docker compose up --build -d --wait --wait-timeout 180
docker compose ps
