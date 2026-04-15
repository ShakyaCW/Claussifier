"""
API tests for POST /classify endpoint.
"""

import pytest
from tests.conftest import RISKY_CLAUSE, SAFE_CLAUSE, SHORT_CLAUSE


@pytest.mark.api
class TestClassifyEndpoint:

    def test_classify_success(self, test_client):
        resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["is_risky"] is True

    def test_classify_safe_clause(self, test_client):
        resp = test_client.post("/classify", json={"clause": SAFE_CLAUSE})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["is_risky"] is False

    def test_classify_missing_clause(self, test_client):
        resp = test_client.post("/classify", json={})
        assert resp.status_code == 422

    def test_classify_clause_too_short(self, test_client):
        resp = test_client.post("/classify", json={"clause": SHORT_CLAUSE})
        assert resp.status_code == 422

    def test_classify_model_not_loaded(self, test_client_no_model):
        resp = test_client_no_model.post("/classify", json={"clause": RISKY_CLAUSE})
        assert resp.status_code == 503

    def test_classify_response_structure(self, test_client):
        resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        body = resp.json()
        assert "status" in body
        assert "data" in body
        data = body["data"]
        assert "clause" in data
        assert "is_risky" in data
        assert "risks_detected" in data
        assert "safe_categories" in data

    def test_classify_explanation_is_none(self, test_client):
        resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        body = resp.json()
        for risk in body["data"]["risks_detected"]:
            assert risk.get("explanation") is None

    def test_classify_includes_attention_data(self, test_client):
        resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        body = resp.json()
        assert "attention_explanation" in body["data"]
        attn = body["data"]["attention_explanation"]
        assert "top_words" in attn
        assert "heatmap_data" in attn
