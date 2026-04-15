"""
API tests for POST /explain endpoint (SSE streaming + static fallback).
"""

import json
import pytest
from tests.conftest import RISKY_CLAUSE, SHORT_CLAUSE, ALL_RISK_TYPES


@pytest.mark.api
class TestExplainEndpoint:

    def test_explain_streaming_response(self, test_client):
        resp = test_client.post(
            "/explain",
            json={"clause": RISKY_CLAUSE, "risk_type": "Unilateral termination"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        events = resp.text.strip().split("\n\n")
        tokens = []
        for event in events:
            if event.startswith("data: "):
                payload = json.loads(event[len("data: "):])
                if "token" in payload:
                    tokens.append(payload["token"])
                elif "done" in payload:
                    assert payload["done"] is True
        assert len(tokens) > 0

    def test_explain_static_fallback_when_unavailable(self, test_client_explainer_unavailable):
        resp = test_client_explainer_unavailable.post(
            "/explain",
            json={"clause": RISKY_CLAUSE, "risk_type": "Arbitration"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "static"
        assert body["streaming"] is False
        assert len(body["explanation"]) > 0

    def test_explain_static_fallback_no_explainer(self, test_client_no_explainer):
        resp = test_client_no_explainer.post(
            "/explain",
            json={"clause": RISKY_CLAUSE, "risk_type": "Arbitration"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "static"

    def test_explain_missing_fields(self, test_client):
        resp = test_client.post("/explain", json={"clause": RISKY_CLAUSE})
        assert resp.status_code == 422

        resp2 = test_client.post("/explain", json={"risk_type": "Arbitration"})
        assert resp2.status_code == 422

    def test_explain_clause_too_short(self, test_client):
        resp = test_client.post(
            "/explain",
            json={"clause": SHORT_CLAUSE, "risk_type": "Arbitration"},
        )
        assert resp.status_code == 422

    def test_explain_all_risk_types(self, test_client_explainer_unavailable):
        for rt in ALL_RISK_TYPES:
            resp = test_client_explainer_unavailable.post(
                "/explain",
                json={"clause": RISKY_CLAUSE, "risk_type": rt},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["explanation"]) > 0
