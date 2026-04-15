"""
API tests for POST /classify-batch and POST /classify-batch-with-attention.
"""

import pytest
from tests.conftest import RISKY_CLAUSE, SAFE_CLAUSE


@pytest.mark.api
class TestBatchClassify:

    def test_batch_classify_success(self, test_client):
        resp = test_client.post(
            "/classify-batch",
            json={"clauses": [RISKY_CLAUSE, SAFE_CLAUSE]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_clauses"] == 2

    def test_batch_classify_empty_list(self, test_client):
        resp = test_client.post("/classify-batch", json={"clauses": []})
        assert resp.status_code == 400

    def test_batch_classify_exceeds_limit(self, test_client):
        clauses = [RISKY_CLAUSE] * 101
        resp = test_client.post("/classify-batch", json={"clauses": clauses})
        assert resp.status_code == 400

    def test_batch_classify_mixed_results(self, test_client):
        resp = test_client.post(
            "/classify-batch",
            json={"clauses": [RISKY_CLAUSE, SAFE_CLAUSE]},
        )
        data = resp.json()["data"]
        assert data["risky_clauses"] >= 1
        assert data["safe_clauses"] >= 1

    def test_batch_summary_counts(self, test_client):
        resp = test_client.post(
            "/classify-batch",
            json={"clauses": [RISKY_CLAUSE, SAFE_CLAUSE, RISKY_CLAUSE]},
        )
        data = resp.json()["data"]
        assert data["total_clauses"] == 3
        assert data["risky_clauses"] + data["safe_clauses"] == 3


@pytest.mark.api
class TestBatchClassifyWithAttention:

    def test_batch_with_attention_success(self, test_client):
        resp = test_client.post(
            "/classify-batch-with-attention",
            json={"clauses": [RISKY_CLAUSE]},
        )
        assert resp.status_code == 200
        results = resp.json()["data"]["results"]
        assert len(results) == 1
        assert "attention_explanation" in results[0]

    def test_batch_with_attention_model_not_loaded(self, test_client_no_model):
        resp = test_client_no_model.post(
            "/classify-batch-with-attention",
            json={"clauses": [RISKY_CLAUSE]},
        )
        assert resp.status_code == 503
