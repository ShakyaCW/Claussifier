"""
Explanation generator using Google Gemini SDK.

Generates context-aware, plain English explanations for detected legal risks.
"""

import os
from typing import Generator, Optional
from pathlib import Path


class GeminiExplainer:
    """Generate dynamic risk explanations using Google Gemini via google-genai SDK."""
    
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
    
    def __init__(self, prompt_path: Optional[str] = None):
        """
        Initialize the explainer via Gemini SDK.
        """
        self.model_name = os.getenv("GEMINI_MODEL", "gemma-3-1b-it")
        self.system_prompt = self._load_system_prompt(prompt_path)
        
        try:
            from google import genai
            from google.genai import types
            
            api_key = os.getenv("GEMINI_API_KEY", "")
            if api_key:
                # Initialize client explicitly with the key 
                # (though it defaults to GEMINI_API_KEY anyway)
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = None
                print("GEMINI_API_KEY not found in environment!")
                
            self.types = types
        except ImportError:
            self.client = None
            self.types = None
            print("google-genai package not installed! Run: pip install google-genai")
            
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
        """Check if Gemini SDK is correctly configured."""
        if self.client is None:
            if not os.getenv("GEMINI_API_KEY"):
                return {
                    'available': False,
                    'message': 'GEMINI_API_KEY is not set.'
                }
            return {
                'available': False,
                'message': 'google-genai Python package is not installed.'
            }
            
        return {
            'available': True,
            'model_name': self.model_name,
            'message': f'{self.model_name} ready via Google Gemini SDK'
        }
    
    def _build_user_prompt(self, clause: str, risk_type: str) -> str:
        """Build the user message for the model."""
        return (
            f"Now generate an explanation for this new clause:\n\n"
            f"Risk Type: {risk_type}\n"
            f'Clause: "{clause}"\n'
            f"Explanation:"
        )
        
    def generate_explanation_stream(
        self, clause: str, risk_type: str
    ) -> Generator[str, None, None]:
        """
        Generate a streaming explanation from Gemini SDK.
        Yields tokens one by one as the model generates them.
        """
        if not self.client:
            print("Gemini client not loaded. Cannot stream.")
            return

        user_prompt = self._build_user_prompt(clause, risk_type)
        
        try:
            config = self.types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=256,
            )
            
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            print(f"Gemini SDK error: {str(e)}")
            # Sometimes models on Gemini do not support system_instruction (like free open models)
            # We can fallback to merging user prompt if an error occurs.
            if "Developer instruction is not enabled" in str(e) or "400" in str(e):
                print("Fallback: merging system prompt into user prompt...")
                try:
                    fallback_config = self.types.GenerateContentConfig(
                        temperature=0.7,
                        top_p=0.9,
                        max_output_tokens=256,
                    )
                    merged_prompt = f"{self.system_prompt}\n\n{user_prompt}"
                    
                    response_stream = self.client.models.generate_content_stream(
                        model=self.model_name,
                        contents=merged_prompt,
                        config=fallback_config
                    )
                    
                    for chunk in response_stream:
                        if chunk.text:
                            yield chunk.text
                except Exception as nested_e:
                    print(f"Gemini SDK nested fallback error: {str(nested_e)}")

    def generate_explanation(self, clause: str, risk_type: str) -> str:
        """Generate a complete (non-streaming) explanation."""
        tokens = list(self.generate_explanation_stream(clause, risk_type))
        if tokens:
            explanation = ''.join(tokens).strip()
            if len(explanation) > 20:
                return explanation
        return self.get_static_explanation(risk_type)
    
    def get_static_explanation(self, risk_type: str) -> str:
        """Get the static fallback explanation for a risk type."""
        return self.STATIC_EXPLANATIONS.get(risk_type, self.DEFAULT_FALLBACK)
