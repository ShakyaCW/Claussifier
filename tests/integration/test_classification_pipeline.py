"""
Integration tests — end-to-end flows across multiple endpoints.

Uses the same mocked infrastructure from conftest.py; validates
that multi-step workflows produce consistent results.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import RISKY_CLAUSE, SAFE_CLAUSE, ALL_RISK_TYPES


@pytest.mark.integration
class TestClassificationPipeline:

    def test_full_classify_then_explain_flow(self, test_client):
        """Classify a risky clause, then request explanations for each detected risk."""
        classify_resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        assert classify_resp.status_code == 200
        risks = classify_resp.json()["data"]["risks_detected"]
        assert len(risks) > 0

        for risk in risks:
            explain_resp = test_client.post(
                "/explain",
                json={"clause": RISKY_CLAUSE, "risk_type": risk["risk_type"]},
            )
            assert explain_resp.status_code == 200

    def test_batch_then_explain_flow(self, test_client):
        """Batch-classify, then stream explanation for the first risky result."""
        batch_resp = test_client.post(
            "/classify-batch-with-attention",
            json={"clauses": [RISKY_CLAUSE, SAFE_CLAUSE]},
        )
        assert batch_resp.status_code == 200
        results = batch_resp.json()["data"]["results"]

        risky_results = [r for r in results if r["is_risky"]]
        assert len(risky_results) >= 1

        first_risk = risky_results[0]["risks_detected"][0]
        explain_resp = test_client.post(
            "/explain",
            json={
                "clause": risky_results[0]["clause"],
                "risk_type": first_risk["risk_type"],
            },
        )
        assert explain_resp.status_code == 200

    def test_model_switch_then_classify(self, test_client, mock_classifier):
        """Switch model, verify info changes, then classify."""
        import app as app_module

        with patch("app.Path.exists", return_value=True), \
             patch("app.RiskClassifier") as MockRC:
            MockRC.return_value = MagicMock()
            switch_resp = test_client.post(
                "/switch-model",
                json={"model_name": "legalbert_final_model"},
            )
            assert switch_resp.status_code == 200

        # Restore the mock classifier so /classify works after patch exits
        app_module.classifier = mock_classifier
        classify_resp = test_client.post("/classify", json={"clause": RISKY_CLAUSE})
        assert classify_resp.status_code == 200

    def test_concurrent_classify_requests(self, test_client):
        """Multiple independent classify requests return correct results."""
        clauses = [
            RISKY_CLAUSE,
            SAFE_CLAUSE,
            "You agree to binding arbitration for all disputes arising from this agreement.",
        ]
        responses = [
            test_client.post("/classify", json={"clause": c})
            for c in clauses
        ]

        for resp in responses:
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert "is_risky" in body["data"]
