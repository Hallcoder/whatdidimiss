from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        # Health endpoint will show db as disconnected since we have no real DB
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_health_has_db_field(self):
        response = client.get("/health")
        data = response.json()
        assert "db" in data

    def test_request_id_header(self):
        response = client.get("/health")
        assert "x-request-id" in response.headers
