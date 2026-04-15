"""
Unit tests for src/inference/risk_explainer.py — RiskExplainer.

Consolidated: covers factory routing, backend availability, streaming,
static fallback, and prompt configuration. OllamaExplainer and
GeminiExplainer are mocked at the class level.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path
import requests


# ---------------------------------------------------------------------------
# Factory routing
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFactoryRouting:

    def test_default_backend_is_ollama(self):
        with patch.dict("os.environ", {}, clear=False), \
             patch("os.environ.get", side_effect=lambda k, d=None: {"EXPLANATION_BACKEND": "ollama"}.get(k, d) if k == "EXPLANATION_BACKEND" else None), \
             patch("src.inference.risk_explainer.OllamaExplainer") as MockOllama, \
             patch("src.inference.risk_explainer.GeminiExplainer"):

            mock_instance = MagicMock()
            mock_instance.is_available.return_value = {"available": False, "message": "test"}
            MockOllama.return_value = mock_instance

            from src.inference.risk_explainer import RiskExplainer
            with patch.dict("os.environ", {"EXPLANATION_BACKEND": "ollama"}):
                explainer = RiskExplainer()
            MockOllama.assert_called_once()

    def test_gemini_backend_selection(self):
        with patch("src.inference.risk_explainer.OllamaExplainer"), \
             patch("src.inference.risk_explainer.GeminiExplainer") as MockGemini:

            mock_instance = MagicMock()
            mock_instance.is_available.return_value = {"available": False, "message": "test"}
            MockGemini.return_value = mock_instance

            with patch.dict("os.environ", {"EXPLANATION_BACKEND": "gemini"}):
                from src.inference.risk_explainer import RiskExplainer
                explainer = RiskExplainer()
            MockGemini.assert_called_once()

    def test_is_dynamic_available_delegates(self):
        with patch("src.inference.risk_explainer.OllamaExplainer") as MockOllama, \
             patch("src.inference.risk_explainer.GeminiExplainer"):

            mock_instance = MagicMock()
            mock_instance.is_available.return_value = {"available": True, "model_name": "test", "message": "ok"}
            MockOllama.return_value = mock_instance

            with patch.dict("os.environ", {"EXPLANATION_BACKEND": "ollama"}):
                from src.inference.risk_explainer import RiskExplainer
                re = RiskExplainer()

            result = re.is_dynamic_available()
            assert result["available"] is True
            mock_instance.is_available.assert_called()


# ---------------------------------------------------------------------------
# Static explanations
# ---------------------------------------------------------------------------

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


@pytest.mark.unit
class TestStaticExplanations:

    @pytest.fixture
    def explainer(self):
        with patch("src.inference.risk_explainer.OllamaExplainer") as MockOllama, \
             patch("src.inference.risk_explainer.GeminiExplainer"):
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = {"available": False, "message": "off"}
            from src.inference.ollama_explainer import OllamaExplainer
            real_explainer = OllamaExplainer.__new__(OllamaExplainer)
            real_explainer.STATIC_EXPLANATIONS = OllamaExplainer.STATIC_EXPLANATIONS
            real_explainer.DEFAULT_FALLBACK = OllamaExplainer.DEFAULT_FALLBACK
            mock_instance.get_static_explanation = lambda rt: real_explainer.STATIC_EXPLANATIONS.get(
                rt, real_explainer.DEFAULT_FALLBACK
            )
            MockOllama.return_value = mock_instance

            with patch.dict("os.environ", {"EXPLANATION_BACKEND": "ollama"}):
                from src.inference.risk_explainer import RiskExplainer
                yield RiskExplainer()

    def test_static_explanation_all_risk_types(self, explainer):
        for rt in ALL_RISK_TYPES:
            explanation = explainer.explain_risk_static(rt)
            assert isinstance(explanation, str)
            assert len(explanation) > 20

    def test_static_explanation_unknown_type(self, explainer):
        explanation = explainer.explain_risk_static("Nonexistent risk type")
        assert "legal rights" in explanation.lower() or "compensation" in explanation.lower()


# ---------------------------------------------------------------------------
# Backend availability (Ollama path)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestOllamaAvailability:

    def test_ollama_available_when_running(self):
        from src.inference.ollama_explainer import OllamaExplainer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "gemma3:1b"}]
        }

        with patch("src.inference.ollama_explainer.requests.get", return_value=mock_response):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            status = exp.is_available()

        assert status["available"] is True

    def test_ollama_unavailable_when_down(self):
        from src.inference.ollama_explainer import OllamaExplainer

        with patch("src.inference.ollama_explainer.requests.get", side_effect=requests.ConnectionError):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            status = exp.is_available()

        assert status["available"] is False
        assert "not running" in status["message"]

    def test_ollama_unavailable_model_not_found(self):
        from src.inference.ollama_explainer import OllamaExplainer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3:8b"}]}

        with patch("src.inference.ollama_explainer.requests.get", return_value=mock_response):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            status = exp.is_available()

        assert status["available"] is False
        assert "not found" in status["message"]


# ---------------------------------------------------------------------------
# Backend availability (Gemini path)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGeminiAvailability:

    def test_gemini_available_with_api_key(self):
        from src.inference.gemini_explainer import GeminiExplainer

        exp = GeminiExplainer.__new__(GeminiExplainer)
        exp.client = MagicMock()  # non-None = initialized
        exp.model_name = "gemma-3-1b-it"
        status = exp.is_available()
        assert status["available"] is True

    def test_gemini_unavailable_no_api_key(self):
        from src.inference.gemini_explainer import GeminiExplainer

        exp = GeminiExplainer.__new__(GeminiExplainer)
        exp.client = None

        with patch.dict("os.environ", {}, clear=False):
            if "GEMINI_API_KEY" in __import__("os").environ:
                del __import__("os").environ["GEMINI_API_KEY"]
            status = exp.is_available()

        assert status["available"] is False
        assert "GEMINI_API_KEY" in status["message"]


# ---------------------------------------------------------------------------
# Streaming & generation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStreamingGeneration:

    def test_stream_yields_tokens(self):
        from src.inference.ollama_explainer import OllamaExplainer

        lines = [
            json.dumps({"response": "This "}).encode(),
            json.dumps({"response": "is "}).encode(),
            json.dumps({"response": "risky.", "done": True}).encode(),
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = lines

        with patch("src.inference.ollama_explainer.requests.post", return_value=mock_response):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            exp.system_prompt = "test prompt"
            exp.timeout = 60

            tokens = list(exp.generate_explanation_stream("clause text", "Arbitration"))

        assert tokens == ["This ", "is ", "risky."]

    def test_stream_connection_error_no_crash(self):
        from src.inference.ollama_explainer import OllamaExplainer

        with patch("src.inference.ollama_explainer.requests.post", side_effect=requests.ConnectionError):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            exp.system_prompt = "test prompt"
            exp.timeout = 60

            tokens = list(exp.generate_explanation_stream("clause", "Arbitration"))
            assert tokens == []

    def test_generate_explanation_joins_tokens(self):
        from src.inference.ollama_explainer import OllamaExplainer

        lines = [
            json.dumps({"response": "This clause is very risky"}).encode(),
            json.dumps({"response": " indeed.", "done": True}).encode(),
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = lines

        with patch("src.inference.ollama_explainer.requests.post", return_value=mock_response):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            exp.system_prompt = "test"
            exp.timeout = 60

            result = exp.generate_explanation("clause", "Arbitration")

        assert "risky" in result

    def test_generate_explanation_fallback_to_static(self):
        from src.inference.ollama_explainer import OllamaExplainer

        with patch("src.inference.ollama_explainer.requests.post", side_effect=requests.ConnectionError):
            exp = OllamaExplainer.__new__(OllamaExplainer)
            exp.ollama_base_url = "http://localhost:11434"
            exp.ollama_model = "gemma3:1b"
            exp.system_prompt = "test"
            exp.timeout = 60

            result = exp.generate_explanation("clause", "Arbitration")

        assert "arbitration" in result.lower() or "court" in result.lower()


# ---------------------------------------------------------------------------
# Configuration — system prompt
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPromptConfiguration:

    def test_system_prompt_loaded_from_file(self, tmp_path):
        prompt_file = tmp_path / "explain_risk.txt"
        prompt_file.write_text("You are a legal expert.", encoding="utf-8")

        from src.inference.ollama_explainer import OllamaExplainer
        exp = OllamaExplainer.__new__(OllamaExplainer)
        result = exp._load_system_prompt(str(prompt_file))
        assert result == "You are a legal expert."

    def test_system_prompt_fallback_when_missing(self):
        from src.inference.ollama_explainer import OllamaExplainer
        exp = OllamaExplainer.__new__(OllamaExplainer)
        result = exp._load_system_prompt("/nonexistent/path/prompt.txt")
        assert "consumer rights" in result.lower()
