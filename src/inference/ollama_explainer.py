"""
Explanation generator using Gemma 3 1B via local Ollama.

Generates context-aware, plain English explanations for detected legal risks.
"""

import json
import os
import requests
from typing import Generator, Optional
from pathlib import Path


class OllamaExplainer:
    """Generate dynamic risk explanations using Gemma 3n via Ollama."""
    
    # Static fallback explanations (used when no backend is available)
    STATIC_EXPLANATIONS = {
        'Limitation of liability': 
            'This clause shields the company from legal responsibility if their service causes you harm, financial loss, or data breaches. Even if they\'re negligent, you likely cannot sue them for damages.',
        'Unilateral termination': 
            'The company can permanently delete your account and all your data at any time, for any reason (or no reason at all), without warning. You have no recourse or appeal process.',
        'Unilateral change': 
            'The company can rewrite these terms whenever they want without notifying you. You might wake up one day to find completely different rules apply to your account and data.',
        'Content removal': 
            'Your posts, files, or content can be deleted at the company\'s sole discretion. They don\'t need to explain why, give you a chance to appeal, or let you retrieve your data first.',
        'Contract by using': 
            'Simply visiting this website or using the app means you\'ve legally agreed to all these terms, even if you\'ve never read them. You can\'t claim you didn\'t know about unfavorable terms later.',
        'Choice of law': 
            'If you have a legal dispute, it will be governed by laws from a different country or state that may not protect consumers as strongly as your local laws do.',
        'Jurisdiction': 
            'Any lawsuit must be filed in a specific court location (often where the company is headquartered), which could be thousands of miles away and prohibitively expensive for you to pursue.',
        'Arbitration': 
            'You give up your right to sue in court or join a class-action lawsuit. Instead, disputes go to private arbitration, which typically favors companies and limits your ability to recover damages.'
    }
    
    DEFAULT_FALLBACK = 'This clause contains terms that may limit your legal rights, protections, or ability to seek compensation if something goes wrong.'
    
    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        timeout: int = 60,
        prompt_path: Optional[str] = None
    ):
        """
        Initialize the explainer.
        
        Args:
            model_name: Model name (default: gemma3n:e2b)
            base_url: API base URL (default: http://localhost:11434)
            timeout: Request timeout in seconds
            prompt_path: Path to the system prompt file
        
        Environment Variables:
            OLLAMA_BASE_URL: Ollama API URL (default: http://localhost:11434)
            OLLAMA_MODEL: Ollama Model name (default: gemma3:1b)
        """
        self.timeout = timeout
        self.system_prompt = self._load_system_prompt(prompt_path)
        
        # Ollama configuration
        self.ollama_base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip('/')
        self.ollama_model = model_name or os.getenv("OLLAMA_MODEL", "gemma3:1b")
    
    def _load_system_prompt(self, prompt_path: Optional[str] = None) -> str:
        """Load the system prompt from file."""
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "explain_risk.txt"
        else:
            prompt_path = Path(prompt_path)
        
        try:
            return prompt_path.read_text(encoding='utf-8').strip()
        except FileNotFoundError:
            print(f"Prompt file not found: {prompt_path}")
            return (
                "You are a consumer rights expert. When given a legal clause and its "
                "risk type, write a 2-3 sentence plain English explanation. Quote specific "
                "phrases from the clause using single quotes. Explain the practical impact "
                "on the user. Only output the explanation, nothing else."
            )
    
    def is_available(self) -> dict:
        """Check if Ollama is running and model is available for generating explanations."""
        return self._check_ollama()
    
    def _check_ollama(self) -> dict:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return {
                    'available': False,
                    'ollama_running': False, 'model_loaded': False,
                    'message': f'Ollama returned status {response.status_code}'
                }
        except requests.ConnectionError:
            return {
                'available': False,
                'ollama_running': False, 'model_loaded': False,
                'message': 'Ollama is not running. Start it with: ollama serve'
            }
        except requests.Timeout:
            return {
                'available': False,
                'ollama_running': False, 'model_loaded': False,
                'message': 'Ollama connection timed out'
            }
        
        try:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            model_found = any(self.ollama_model in name for name in model_names)
            
            if model_found:
                return {
                    'available': True,
                    'ollama_running': True, 'model_loaded': True,
                    'model_name': self.ollama_model,
                    'message': f'{self.ollama_model} ready via Ollama (local)'
                }
            else:
                return {
                    'available': False,
                    'ollama_running': True, 'model_loaded': False,
                    'message': f'Model "{self.ollama_model}" not found. Run: ollama pull {self.ollama_model}'
                }
        except Exception as e:
            return {
                'available': False,
                'ollama_running': True, 'model_loaded': False,
                'message': f'Error checking models: {str(e)}'
            }
    
    def _build_user_prompt(self, clause: str, risk_type: str) -> str:
        """Build the user message for the model."""
        return (
            f"Now generate an explanation for this new clause:\n\n"
            f"Risk Type: {risk_type}\n"
            f'Clause: "{clause}"\n'
            f"Explanation:"
        )
    
    # ================================================================
    # OLLAMA BACKEND
    # ================================================================
    
    def _stream_ollama(self, clause: str, risk_type: str) -> Generator[str, None, None]:
        """Stream tokens from local Ollama."""
        user_prompt = self._build_user_prompt(clause, risk_type)
        
        payload = {
            "model": self.ollama_model,
            "system": self.system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 256,
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload, stream=True, timeout=self.timeout
            )
            
            if response.status_code != 200:
                print(f"Ollama returned status {response.status_code}")
                return
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get('response', '')
                        if token:
                            yield token
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except requests.ConnectionError:
            print("Cannot connect to Ollama. Is it running?")
        except requests.Timeout:
            print(f"Ollama request timed out after {self.timeout}s")
        except Exception as e:
            print(f"Ollama error: {e}")
    
    # ================================================================
    # PUBLIC API
    # ================================================================
    
    def generate_explanation_stream(
        self, clause: str, risk_type: str
    ) -> Generator[str, None, None]:
        """
        Generate a streaming explanation from Ollama.
        
        Yields tokens one by one as the model generates them.
        
        Args:
            clause: The legal clause text
            risk_type: The identified risk category
            
        Yields:
            str: Individual tokens as they are generated
        """
        yield from self._stream_ollama(clause, risk_type)
    
    def generate_explanation(self, clause: str, risk_type: str) -> str:
        """
        Generate a complete (non-streaming) explanation.
        
        Returns:
            Complete explanation string, or static fallback on failure
        """
        tokens = list(self.generate_explanation_stream(clause, risk_type))
        
        if tokens:
            explanation = ''.join(tokens).strip()
            if len(explanation) > 20:
                return explanation
        
        return self.get_static_explanation(risk_type)
    
    def get_static_explanation(self, risk_type: str) -> str:
        """Get the static fallback explanation for a risk type."""
        return self.STATIC_EXPLANATIONS.get(risk_type, self.DEFAULT_FALLBACK)
