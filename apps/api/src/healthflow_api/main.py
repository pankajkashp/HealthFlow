"""HealthFlow API application factory.

Creates and configures the FastAPI application instance.

Architecture position: API layer (apps/api).
This module wires together the API application and its routes.
No business logic belongs here. Routes delegate to the application layer.

Ref: docs/architecture/ARCHITECTURE.md §2.2, §16
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from healthflow_api.health import router as health_router
from healthflow_api.routes.cases import router as cases_router

app = FastAPI(
    title="HealthFlow API",
    version="0.1.0",
    description=(
        "HealthFlow prior-authorization workflow API. "
        "Accepts requests from the Next.js frontend and delegates to the application layer."
    ),
)

# CORS — Phase 6: the Next.js dashboard (a different origin) calls this API directly.
# JWT auth (AD-011) is explicitly deferred for the hackathon MVP demo; see
# docs/phases/PHASE_06_WALKTHROUGH.md, decision 4.
_web_origin = os.getenv("WEB_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_web_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & Readiness checks — Phase 1 foundation.
app.include_router(health_router, prefix="/api/v1")
# Case workflow — Phase 6.
app.include_router(cases_router, prefix="/api/v1")
