"""Health and readiness routers for the HealthFlow API.

Provides:
- GET /api/v1/health: Liveness check to confirm API process is running.
- GET /api/v1/readiness: Readiness check to confirm API is ready to accept traffic.

These endpoints contain no business logic and make no external or database calls in Phase 1.
Ref: Phase 1 specification §2, §9, §11.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="API health check")
def health_check() -> dict[str, str]:
    """Return a health check response confirming the API process is alive."""
    return {"status": "healthy", "service": "healthflow-api"}


@router.get("/readiness", summary="API readiness check")
def readiness_check() -> dict[str, str]:
    """Return a readiness response confirming the API is ready to receive requests."""
    return {"status": "ready", "service": "healthflow-api"}
