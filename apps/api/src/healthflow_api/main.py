"""HealthFlow API application factory.

Creates and configures the FastAPI application instance.

Architecture position: API layer (apps/api).
This module wires together the API application and its routes.
No business logic belongs here. Routes delegate to the application layer.

Ref: docs/architecture/ARCHITECTURE.md §2.2, §16
"""

from fastapi import FastAPI

from healthflow_api.health import router as health_router

app = FastAPI(
    title="HealthFlow API",
    version="0.1.0",
    description=(
        "HealthFlow prior-authorization workflow API. "
        "Accepts requests from the Next.js frontend and delegates to the application layer."
    ),
)

# Health & Readiness checks — Phase 1 foundation.
app.include_router(health_router, prefix="/api/v1")
