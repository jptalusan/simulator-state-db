"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from simulation_db.api.app import app


client = TestClient(app)


def test_health():
    """Test health check endpoint."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_get_simulations():
    """Test list simulations endpoint."""
    r = client.get("/simulations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
