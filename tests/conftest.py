"""
Shared test fixtures for Claussifier test suite.

Provides mock classifier, mock explainers, FastAPI test client,
sample data, and synthetic attention tensors so all tests run
without real model weights or external services.

NOTE: torch/transformers are NOT imported at module level so that
API and integration tests work even when only fastapi+httpx are installed.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

RISKY_CLAUSE = "We may terminate your account at any time without prior notice."
SAFE_CLAUSE = "We value your privacy and are committed to protecting your personal information at all times carefully."
SHORT_CLAUSE = "Short."

ALL_RISK_TYPES = [
    "Limitation of liability",
    "Unilateral termination",
    "Unilateral change",
    "Content removal",
    "Contract by using",
    "Choice of law",
    "Jurisdiction",
    "Arbitration",
]


@pytest.fixture
def sample_clauses():
    return {
        "risky": RISKY_CLAUSE,
        "safe": SAFE_CLAUSE,
        "short": SHORT_CLAUSE,
    }


# ---------------------------------------------------------------------------
# Synthetic BERT outputs (lazy import — only used by unit tests)
# ---------------------------------------------------------------------------

def _make_attention_tensors(seq_len=20, n_layers=12, n_heads=12):
    import torch
    return tuple(
        torch.rand(1, n_heads, seq_len, seq_len) for _ in range(n_layers)
    )


@pytest.fixture
def sample_attention_tensors():
    return _make_attention_tensors()


# ---------------------------------------------------------------------------
# Mock RiskClassifier (pure MagicMock — no torch import needed)
# ---------------------------------------------------------------------------

def _build_classify_result(clause, is_risky):
    if is_risky:
        return {
            "clause": clause,
            "is_risky": True,
            "risks_detected": [
                {"risk_type": "Unilateral termination", "confidence": 0.95, "threshold": 0.5}
            ],
            "safe_categories": [
                "Limitation of liability", "Unilateral change", "Content removal",
                "Contract by using", "Choice of law", "Jurisdiction", "Arbitration",
            ],
        }
    return {
        "clause": clause,
        "is_risky": False,
        "risks_detected": [],
        "safe_categories": list(ALL_RISK_TYPES),
    }


def _build_classify_with_attention_result(clause, is_risky):
    result = _build_classify_result(clause, is_risky)
    result["attention_explanation"] = {
        "tokens": ["terminate", "account", "without", "notice"],
        "importance_scores": [0.25, 0.20, 0.15, 0.10],
        "top_words": [
            {"word": "terminate", "importance": 0.25, "position": 0},
            {"word": "account", "importance": 0.20, "position": 1},
        ],
        "heatmap_data": [
            {"word": "terminate", "importance": 0.25, "normalized": 1.0},
            {"word": "account", "importance": 0.20, "normalized": 0.8},
        ],
    }
    return result


def _is_risky(clause):
    return any(kw in clause.lower() for kw in ("terminate", "liable", "arbitration", "governed"))


@pytest.fixture
def mock_classifier():
    clf = MagicMock()
    clf.LABEL_NAMES = list(ALL_RISK_TYPES)
    clf.thresholds = [0.5] * 8

    def _classify(clause, return_all_scores=False):
        risky = _is_risky(clause)
        result = _build_classify_result(clause, risky)
        if return_all_scores:
            result["all_scores"] = [
                {"risk_type": rt, "confidence": 0.95 if rt == "Unilateral termination" and risky else 0.05,
                 "threshold": 0.5, "predicted": rt == "Unilateral termination" and risky}
                for rt in ALL_RISK_TYPES
            ]
        return result

    def _classify_with_attention(clause, return_all_scores=False):
        risky = _is_risky(clause)
        result = _build_classify_with_attention_result(clause, risky)
        if return_all_scores:
            result["all_scores"] = [
                {"risk_type": rt, "confidence": 0.95 if rt == "Unilateral termination" and risky else 0.05,
                 "threshold": 0.5, "predicted": rt == "Unilateral termination" and risky}
                for rt in ALL_RISK_TYPES
            ]
        return result

    def _classify_batch(clauses, batch_size=16, return_all_scores=False):
        return [_classify(c, return_all_scores) for c in clauses]

    clf.classify = MagicMock(side_effect=_classify)
    clf.classify_with_attention = MagicMock(side_effect=_classify_with_attention)
    clf.classify_batch = MagicMock(side_effect=_classify_batch)
    clf.get_model_info.return_value = {
        "model_name": "BERT Risk Detector",
        "model_type": "bert-base-uncased",
        "num_labels": 8,
        "label_names": list(ALL_RISK_TYPES),
        "thresholds": [0.5] * 8,
        "device": "cpu",
        "model_dir": "src/models/legalbert_with_augmentation_final_model",
    }
    return clf


# ---------------------------------------------------------------------------
# Mock explainer (for dynamic_explainer in app.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_explainer_available():
    exp = MagicMock()
    exp.is_available.return_value = {"available": True, "model_name": "mock-model", "message": "ready"}

    def _stream(clause, risk_type):
        for token in ["This ", "clause ", "is ", "risky."]:
            yield token

    exp.generate_explanation_stream = MagicMock(side_effect=_stream)
    exp.get_static_explanation = MagicMock(
        side_effect=lambda rt: f"Static explanation for {rt}"
    )
    return exp


@pytest.fixture
def mock_explainer_unavailable():
    exp = MagicMock()
    exp.is_available.return_value = {"available": False, "message": "Backend down"}
    exp.get_static_explanation = MagicMock(
        side_effect=lambda rt: f"Static explanation for {rt}"
    )
    return exp


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked globals
# ---------------------------------------------------------------------------

def _inject_and_yield(app_module, client, overrides):
    """
    Apply overrides to app_module globals AFTER the TestClient has been
    created (i.e. after the @app.on_event("startup") handler has already
    fired), then restore originals on teardown.
    """
    originals = {key: getattr(app_module, key, None) for key in overrides}
    for key, value in overrides.items():
        setattr(app_module, key, value)
    yield client
    for key, value in originals.items():
        setattr(app_module, key, value)


@pytest.fixture
def test_client(mock_classifier, mock_explainer_available):
    import app as app_module
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield from _inject_and_yield(app_module, client, {
            "classifier": mock_classifier,
            "current_model_name": "legalbert_with_augmentation_final_model",
            "dynamic_explainer": mock_explainer_available,
            "risk_explainer": MagicMock(),
        })


@pytest.fixture
def test_client_no_model(mock_explainer_available):
    import app as app_module
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield from _inject_and_yield(app_module, client, {
            "classifier": None,
            "dynamic_explainer": mock_explainer_available,
        })


@pytest.fixture
def test_client_no_explainer(mock_classifier):
    import app as app_module
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield from _inject_and_yield(app_module, client, {
            "classifier": mock_classifier,
            "dynamic_explainer": None,
        })


@pytest.fixture
def test_client_explainer_unavailable(mock_classifier, mock_explainer_unavailable):
    import app as app_module
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield from _inject_and_yield(app_module, client, {
            "classifier": mock_classifier,
            "dynamic_explainer": mock_explainer_unavailable,
        })
