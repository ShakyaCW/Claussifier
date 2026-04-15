"""
API tests for POST /switch-model endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


@pytest.mark.api
class TestSwitchModelEndpoint:

    def test_switch_to_valid_model(self, test_client):
        with patch("app.Path.exists", return_value=True), \
             patch("app.RiskClassifier") as MockRC:
            mock_clf = MagicMock()
            MockRC.return_value = mock_clf

            resp = test_client.post(
                "/switch-model",
                json={"model_name": "legalbert_final_model"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["current_model"] == "legalbert_final_model"

    def test_switch_missing_model_name(self, test_client):
        resp = test_client.post("/switch-model", json={})
        assert resp.status_code == 400

    def test_switch_invalid_model_name(self, test_client):
        resp = test_client.post(
            "/switch-model",
            json={"model_name": "nonexistent_model"},
        )
        assert resp.status_code == 400
        assert "Invalid model" in resp.json()["detail"]

    def test_switch_model_dir_not_found(self, test_client):
        with patch("app.Path.exists", return_value=False):
            resp = test_client.post(
                "/switch-model",
                json={"model_name": "bert_final_model"},
            )
            assert resp.status_code == 404
