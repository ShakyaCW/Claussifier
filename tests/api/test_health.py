"""
API tests for GET /health endpoint.
"""

import pytest


@pytest.mark.api
class TestHealthEndpoint:

    def test_health_model_loaded(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["model_loaded"] is True

    def test_health_model_not_loaded(self, test_client_no_model):
        resp = test_client_no_model.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "model_not_loaded"
        assert body["model_loaded"] is False
