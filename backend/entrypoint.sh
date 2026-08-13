#!/bin/sh
# Container entrypoint: migrate -> seed-if-empty -> serve.
#
# `set -eu` means any failing command (a non-zero exit from `alembic upgrade head` in
# particular) aborts the script immediately, before `exec uvicorn` is ever reached — the
# container exits non-zero and never serves a database that migrations left half-applied.
#
# Migrations and seeding run here, in the running container, rather than in CI: RDS is
# not publicly accessible, so the only thing on this deployment's critical path that both
# reaches the database and runs on every deploy is the container itself.
set -eu

echo "Running Alembic migrations..."
alembic upgrade head

echo "Wiping old-brand demo data if the pre-rebrand corpus is still present..."
python -m ugjcs.scripts.rebrand_wipe

echo "Seeding demo corpus and judge accounts if the database is empty..."
python -m ugjcs.scripts.seed_demo --if-empty

echo "Pruning manuscripts left behind by live verification runs..."
python -m ugjcs.scripts.prune_junk

echo "Starting API server..."
exec uvicorn ugjcs.api.main:app --host 0.0.0.0 --port 8000
