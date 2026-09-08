# HealthFlow API — Dockerfile for local development
#
# Base image: Python 3.13 slim (matches required-python in pyproject.toml)
# Purpose: Run the FastAPI application, wired to the agent runtime and Postgres, via Docker Compose.
#
# Phase 6: apps/api now depends on the monorepo's other Python packages (packages/domain,
# packages/application, packages/infrastructure, services/agent, etc. — installed as local editable
# packages, since they're referenced by bare name in each pyproject.toml's dependencies, not by
# path or version). That means this build's context must be the REPO ROOT (see docker-compose.yml's
# `api.build.context: ..`), not apps/api alone as in earlier phases — this Dockerfile now needs to
# reach every packages/* and services/agent/ directory to install them.
#
# Ref: docs/architecture/ARCHITECTURE.md §2.2, §4.1
# Ref: docs/phases/PHASE_06_WALKTHROUGH.md, decision 3

FROM python:3.13-slim

# Non-root user for least privilege
RUN useradd --create-home appuser
WORKDIR /app

# Install build dependencies needed by pip (and psycopg's C extension)
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the whole monorepo (build context is the repo root — see docker-compose.yml)
COPY packages/ ./packages/
COPY services/ ./services/
COPY apps/api/ ./apps/api/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY alembic.ini ./alembic.ini

# Install in dependency order: domain/shared first, then everything that depends on them.
RUN pip install --no-cache-dir \
    -e packages/domain \
    -e packages/shared \
    -e packages/safety \
    -e packages/application \
    -e packages/infrastructure \
    -e services/agent \
    -e apps/api

USER appuser

WORKDIR /app/apps/api

# Expose the API port (matches API_PORT in .env.example)
EXPOSE 8000

# Development entrypoint: run migrations + seed the demo benchmark patients, then start with
# hot reload. Safe to re-run — both the migration and the seed script are idempotent.
CMD ["sh", "-c", "cd /app && alembic upgrade head && python scripts/seed_demo_data.py && cd apps/api && uvicorn healthflow_api.main:app --host 0.0.0.0 --port 8000 --reload"]
