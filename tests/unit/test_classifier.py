"""
Unit tests for src/inference/classifier.py — RiskClassifier.

All BERT model loading and inference is mocked so tests run
without real model weights.
"""

import json
import pytest
import torch
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from src.inference.classifier import RiskClassifier


# ---------------------------------------------------------------------------
# Helpers to build mock BERT outputs
# ---------------------------------------------------------------------------

def _mock_model_output(logits, attentions=None):
    out = MagicMock()
    out.logits = logits
    out.attentions = attentions
    return out


def _risky_logits():
    logits = torch.full((1, 8), -2.0)
    logits[0, 1] = 3.0  # Unilateral termination fires
    return logits


def _safe_logits():
    return torch.full((1, 8), -3.0)


def _make_attentions(seq_len=20):
    return tuple(torch.rand(1, 12, seq_len, seq_len) for _ in range(12))


# ---------------------------------------------------------------------------
# Fixture: a fully-mocked RiskClassifier instance
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    """Instantiate RiskClassifier with mocked model loading."""
    with patch("src.inference.classifier.BertTokenizer") as MockTokenizer, \
         patch("src.inference.classifier.BertForSequenceClassification") as MockModel:

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.zeros(1, 20, dtype=torch.long),
            "attention_mask": torch.ones(1, 20, dtype=torch.long),
        }
        # convert_ids_to_tokens used in classify_with_attention
        mock_tokenizer.convert_ids_to_tokens.return_value = (
            ["[CLS]"] + ["terminate", "your", "account", "at", "any",
                         "time", "without", "prior", "notice", "."] +
            ["[SEP]"] + ["[PAD]"] * 8
        )
        MockTokenizer.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.config = MagicMock()
        mock_model.config.output_attentions = True
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = None

        attentions = _make_attentions()
        mock_model.return_value = _mock_model_output(_risky_logits(), attentions)
        mock_model.side_effect = None
        mock_model.__call__ = MagicMock(
            return_value=_mock_model_output(_risky_logits(), attentions)
        )

        MockModel.from_pretrained.return_value = mock_model

        clf = RiskClassifier(model_dir="src/models/fake_model", device="cpu")
        clf._mock_model = mock_model
        yield clf


@pytest.fixture
def safe_classifier():
    """A classifier whose model returns safe (all-negative) logits."""
    with patch("src.inference.classifier.BertTokenizer") as MockTokenizer, \
         patch("src.inference.classifier.BertForSequenceClassification") as MockModel:

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.zeros(1, 20, dtype=torch.long),
            "attention_mask": torch.ones(1, 20, dtype=torch.long),
        }
        mock_tokenizer.convert_ids_to_tokens.return_value = (
            ["[CLS]"] + ["we", "value", "your", "privacy"] + ["[SEP]"] + ["[PAD]"] * 14
        )
        MockTokenizer.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.config = MagicMock()
        mock_model.config.output_attentions = True
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = None

        attentions = _make_attentions()
        mock_model.return_value = _mock_model_output(_safe_logits(), attentions)

        MockModel.from_pretrained.return_value = mock_model

        clf = RiskClassifier(model_dir="src/models/fake_model", device="cpu")
        yield clf


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestClassifyStructure:

    def test_classify_returns_correct_structure(self, classifier):
        result = classifier.classify("We may terminate your account at any time.")
        assert "clause" in result
        assert "is_risky" in result
        assert "risks_detected" in result
        assert "safe_categories" in result

    def test_classify_risky_clause(self, classifier):
        result = classifier.classify("We may terminate your account at any time.")
        assert result["is_risky"] is True
        risk_types = [r["risk_type"] for r in result["risks_detected"]]
        assert "Unilateral termination" in risk_types

    def test_classify_safe_clause(self, safe_classifier):
        result = safe_classifier.classify("We value your privacy and protect your data.")
        assert result["is_risky"] is False
        assert len(result["risks_detected"]) == 0

    def test_classify_with_all_scores(self, classifier):
        result = classifier.classify("We may terminate your account.", return_all_scores=True)
        assert "all_scores" in result
        assert len(result["all_scores"]) == 8

    def test_classify_with_attention_structure(self, classifier):
        result = classifier.classify_with_attention("We may terminate your account.")
        assert "attention_explanation" in result
        attn = result["attention_explanation"]
        assert "tokens" in attn
        assert "top_words" in attn
        assert "heatmap_data" in attn

    def test_risks_sorted_by_confidence(self, classifier):
        result = classifier.classify("We may terminate your account.")
        confs = [r["confidence"] for r in result["risks_detected"]]
        assert confs == sorted(confs, reverse=True)


@pytest.mark.unit
class TestThresholds:

    def test_thresholds_loaded_from_json(self, tmp_path):
        thresholds_data = {"optimal_thresholds": [0.3, 0.4, 0.5, 0.6, 0.7, 0.35, 0.45, 0.55]}
        thresholds_file = tmp_path / "optimal_thresholds.json"
        thresholds_file.write_text(json.dumps(thresholds_data))

        with patch("src.inference.classifier.BertTokenizer") as MockTok, \
             patch("src.inference.classifier.BertForSequenceClassification") as MockMod:
            MockTok.from_pretrained.return_value = MagicMock()
            mock_model = MagicMock()
            mock_model.config = MagicMock()
            mock_model.to.return_value = mock_model
            MockMod.from_pretrained.return_value = mock_model

            clf = RiskClassifier(
                model_dir="src/models/fake_model",
                thresholds_path=str(thresholds_file),
                device="cpu",
            )
            assert clf.thresholds == [0.3, 0.4, 0.5, 0.6, 0.7, 0.35, 0.45, 0.55]

    def test_thresholds_default_fallback(self):
        with patch("src.inference.classifier.BertTokenizer") as MockTok, \
             patch("src.inference.classifier.BertForSequenceClassification") as MockMod:
            MockTok.from_pretrained.return_value = MagicMock()
            mock_model = MagicMock()
            mock_model.config = MagicMock()
            mock_model.to.return_value = mock_model
            MockMod.from_pretrained.return_value = mock_model

            clf = RiskClassifier(
                model_dir="src/models/fake_model",
                thresholds_path="nonexistent/path.json",
                device="cpu",
            )
            assert clf.thresholds == [0.5] * 8


@pytest.mark.unit
class TestBatch:

    def test_classify_batch_returns_list(self, classifier):
        clauses = [
            "We may terminate your account.",
            "This agreement is governed by California law.",
        ]
        results = classifier.classify_batch(clauses)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_classify_batch_empty_list(self, classifier):
        results = classifier.classify_batch([])
        assert results == []


@pytest.mark.unit
class TestMiscellaneous:

    def test_device_selection(self):
        with patch("src.inference.classifier.BertTokenizer") as MockTok, \
             patch("src.inference.classifier.BertForSequenceClassification") as MockMod:
            MockTok.from_pretrained.return_value = MagicMock()
            mock_model = MagicMock()
            mock_model.config = MagicMock()
            mock_model.to.return_value = mock_model
            MockMod.from_pretrained.return_value = mock_model

            clf = RiskClassifier(model_dir="src/models/fake", device="cpu")
            assert str(clf.device) == "cpu"

    def test_label_names_count(self):
        assert len(RiskClassifier.LABEL_NAMES) == 8
