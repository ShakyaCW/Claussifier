"""
Risk explanation generator.
Uses Ollama or Google Gemini via SDK for dynamic explanations with static fallback.
"""

import os
from typing import Dict, List
from src.inference.ollama_explainer import OllamaExplainer
from src.inference.gemini_explainer import GeminiExplainer


class RiskExplainer:
    """Generate user-friendly explanations for risk classifications."""
    
    def __init__(self):
        """Initialize the risk explainer with the configured backend."""
        self.backend_type = os.getenv("EXPLANATION_BACKEND", "ollama").lower()
        
        if self.backend_type == "gemini":
            self.explainer = GeminiExplainer()
        else:
            self.explainer = OllamaExplainer()
            
        # Check availability on init
        status = self.explainer.is_available()
        if status['available']:
            provider_name = "Ollama" if self.backend_type == "ollama" else "Gemini SDK"
            print(f"Dynamic explanations ready ({status['model_name']} via {provider_name})")
        else:
            print(f"Dynamic explanations unavailable: {status['message']}")
            print("Falling back to static explanations.")
    
    def explain_risk_static(self, risk_type: str) -> str:
        """
        Get the static (hardcoded) explanation for a risk type.
        Used for instant display before dynamic explanation loads.
        
        Args:
            risk_type: Type of risk detected
            
        Returns:
            Static explanation string
        """
        return self.explainer.get_static_explanation(risk_type)
    
    def explain_risk(
        self,
        clause: str,
        risk_type: str,
        confidence: float,
        top_words: List[Dict]
    ) -> str:
        """
        Generate a static explanation for a risky clause.
        Used during classification for instant results.
        Dynamic explanations are generated on-demand via /explain endpoint.
        
        Args:
            clause: The clause text
            risk_type: Type of risk detected
            confidence: Model confidence (0-1)
            top_words: Top influential words from attention
        
        Returns:
            Static explanation string
        """
        return self.explain_risk_static(risk_type)
    
    def is_dynamic_available(self) -> dict:
        """Check if dynamic explanations are available."""
        return self.explainer.is_available()
