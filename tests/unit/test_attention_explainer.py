"""
Unit tests for src/inference/attention_explainer.py — AttentionExplainer.

Uses synthetic attention tensors; no real model required.
"""

import pytest
import torch
import numpy as np
from unittest.mock import MagicMock

from src.inference.attention_explainer import AttentionExplainer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_attentions(seq_len=20, n_layers=12, n_heads=12):
    torch.manual_seed(42)
    return tuple(torch.rand(1, n_heads, seq_len, seq_len) for _ in range(n_layers))


def _make_tokenizer_and_ids(tokens):
    """Return (mock_tokenizer, input_ids tensor) for given token list."""
    tokenizer = MagicMock()
    tokenizer.convert_ids_to_tokens.return_value = tokens
    input_ids = torch.arange(len(tokens)).unsqueeze(0)
    return tokenizer, input_ids


# ---------------------------------------------------------------------------
# Tests — aggregate_attention
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAggregateAttention:

    def test_aggregate_attention_shape(self):
        attentions = _make_attentions(seq_len=30)
        result = AttentionExplainer.aggregate_attention(attentions)
        assert result.shape == (30, 30)

    def test_aggregate_attention_none_raises(self):
        with pytest.raises(ValueError):
            AttentionExplainer.aggregate_attention(None)

    def test_aggregate_attention_empty_raises(self):
        with pytest.raises(ValueError):
            AttentionExplainer.aggregate_attention(())


# ---------------------------------------------------------------------------
# Tests — get_token_importance
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTokenImportance:

    def test_cls_method(self):
        matrix = np.random.rand(10, 10).astype(np.float32)
        importance = AttentionExplainer.get_token_importance(matrix, method="cls")
        np.testing.assert_array_equal(importance, matrix[0, :])

    def test_mean_method(self):
        matrix = np.random.rand(10, 10).astype(np.float32)
        importance = AttentionExplainer.get_token_importance(matrix, method="mean")
        np.testing.assert_array_almost_equal(importance, matrix.mean(axis=0))

    def test_invalid_method_raises(self):
        matrix = np.random.rand(10, 10).astype(np.float32)
        with pytest.raises(ValueError, match="Unknown method"):
            AttentionExplainer.get_token_importance(matrix, method="invalid")


# ---------------------------------------------------------------------------
# Tests — explain_prediction
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestExplainPrediction:

    @pytest.fixture
    def explainer_result(self):
        tokens = (
            ["[CLS]"] +
            ["dis", "##claim", "all", "liability", "for", "damages", "arising", "."] +
            ["[SEP]"] + ["[PAD]"] * 10
        )
        tokenizer, input_ids = _make_tokenizer_and_ids(tokens)
        attentions = _make_attentions(seq_len=len(tokens))

        explainer = AttentionExplainer()
        return explainer.explain_prediction(
            input_ids=input_ids,
            attentions=attentions,
            tokenizer=tokenizer,
            top_k=5,
        )

    def test_structure(self, explainer_result):
        assert "tokens" in explainer_result
        assert "importance_scores" in explainer_result
        assert "top_words" in explainer_result
        assert "heatmap_data" in explainer_result

    def test_special_tokens_excluded(self, explainer_result):
        all_tokens = explainer_result["tokens"]
        for special in ["[CLS]", "[SEP]", "[PAD]"]:
            assert special not in all_tokens

    def test_subword_merging(self, explainer_result):
        assert "disclaim" in explainer_result["tokens"]

    def test_stopwords_zeroed(self, explainer_result):
        tokens = explainer_result["tokens"]
        scores = explainer_result["importance_scores"]
        stopwords = {"all", "for"}
        for tok, score in zip(tokens, scores):
            if tok.lower() in stopwords:
                assert score == 0.0

    def test_punctuation_filtered_from_top_words(self, explainer_result):
        top_word_texts = [w["word"] for w in explainer_result["top_words"]]
        assert "." not in top_word_texts

    def test_top_k_limit(self, explainer_result):
        assert len(explainer_result["top_words"]) <= 5

    def test_heatmap_normalization(self, explainer_result):
        if explainer_result["heatmap_data"]:
            max_norm = max(h["normalized"] for h in explainer_result["heatmap_data"])
            assert 0.0 < max_norm <= 1.0 + 1e-9
