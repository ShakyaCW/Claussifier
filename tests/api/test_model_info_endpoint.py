"""
API tests for GET /model-info endpoint.
"""

import pytest


@pytest.mark.api
class TestModelInfoEndpoint:

    def test_model_info_success(self, test_client):
        resp = test_client.get("/model-info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "data" in body
        assert "current_model" in body

    def test_model_info_model_not_loaded(self, test_client_no_model):
        resp = test_client_no_model.get("/model-info")
        assert resp.status_code == 503

    def test_model_info_response_fields(self, test_client):
        resp = test_client.get("/model-info")
        data = resp.json()["data"]
        assert "model_name" in data
        assert "model_type" in data
        assert "f1_score" in data
        assert "precision" in data
        assert "recall" in data
