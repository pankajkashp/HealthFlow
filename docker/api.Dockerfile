# HealthFlow API — Dockerfile for local development
#
# Base image: Python 3.13 slim (matches required-python in pyproject.toml)
# Purpose: Run the FastAPI application during local development via Docker Compose.
#
# This Dockerfile supports Phase 1 ONLY. It does NOT configure:
# - PostgreSQL connection (Phase 1 has no database)
# - Bedrock / Claude / Strands (agent phase is later)
# - Production secrets (no secrets are embedded here)
#
# Ref: docs/architecture/ARCHITECTURE.md §2.2, §4.1
# Ref: Phase 1 specification §6 (Docker foundation)

FROM python:3.13-slim

# Non-root user for least privilege
RUN useradd --create-home appuser
WORKDIR /app

# Install build dependencies needed by pip
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first to allow Docker layer caching
COPY pyproject.toml ./

# Install production dependencies
RUN pip install --no-cache-dir -e "."

# Copy application source
COPY src/ ./src/

USER appuser

# Expose the API port (matches API_PORT in .env.example)
EXPOSE 8000

# Development entrypoint: hot reload enabled
CMD ["uvicorn", "healthflow_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
