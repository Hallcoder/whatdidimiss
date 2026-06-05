from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestErrorHandling:
    def test_unauthenticated_request_returns_401(self):
        response = client.get("/api/v1/videos")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_error_response_has_request_id(self):
        response = client.get("/api/v1/videos")
        data = response.json()
        assert data["error"]["request_id"] is not None

    def test_missing_auth_header(self):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_invalid_bearer_token(self):
        response = client.get(
            "/api/v1/videos",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"
