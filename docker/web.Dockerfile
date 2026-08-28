# HealthFlow Web — Dockerfile for local development
#
# Base image: Node.js 22 LTS Alpine (matches Node 22 on the host system)
# Purpose: Run the Next.js development server during local development via Docker Compose.
#
# This Dockerfile supports Phase 1 ONLY. It does NOT configure:
# - Production build / export
# - API keys or secrets
# - AWS services
#
# Ref: docs/architecture/ARCHITECTURE.md §2.1, §4.2
# Ref: Phase 1 specification §6 (Docker foundation)

FROM node:22-alpine

# Non-root user for least privilege
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app

# Copy package manifests first for Docker layer caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy application source
COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

# Expose the Next.js dev server port
EXPOSE 3000

# Development entrypoint with hot reload
CMD ["npm", "run", "dev"]
