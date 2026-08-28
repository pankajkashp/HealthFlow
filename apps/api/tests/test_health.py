"""Tests for the health check endpoint.

These tests verify that the API foundation starts correctly and that the
health endpoint responds as expected.

Ref: Phase 1 specification §10 (Testing foundation).
"""

from fastapi.testclient import TestClient

from healthflow_api.main import app

client = TestClient(app)


def test_health_returns_http_200() -> None:
    """GET /api/v1/health must return HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_contains_status() -> None:
    """GET /api/v1/health must return status: healthy."""
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "healthy"


def test_health_response_identifies_service() -> None:
    """GET /api/v1/health must identify the healthflow-api service."""
    response = client.get("/api/v1/health")
    body = response.json()
    assert body["service"] == "healthflow-api"
