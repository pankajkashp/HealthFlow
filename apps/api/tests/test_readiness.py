"""Tests for the readiness check endpoint.

These tests verify that the API foundation reports readiness as expected.

Ref: Phase 1 specification §10 (Testing foundation).
"""

from fastapi.testclient import TestClient

from healthflow_api.main import app

client = TestClient(app)


def test_readiness_returns_http_200() -> None:
    """GET /api/v1/readiness must return HTTP 200."""
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200


def test_readiness_response_contains_status() -> None:
    """GET /api/v1/readiness must return status: ready."""
    response = client.get("/api/v1/readiness")
    body = response.json()
    assert body["status"] == "ready"


def test_readiness_response_identifies_service() -> None:
    """GET /api/v1/readiness must identify the healthflow-api service."""
    response = client.get("/api/v1/readiness")
    body = response.json()
    assert body["service"] == "healthflow-api"
