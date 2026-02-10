"""
Risk explanation generator using template-based explanations.
Provides clear, user-focused explanations for detected risks.
"""

from typing import Dict, List


class RiskExplainer:
    """Generate user-friendly explanations for risk classifications."""
    
    def __init__(self):
        """Initialize the risk explainer."""
        pass
    
    def explain_risk(
        self,
        clause: str,
        risk_type: str,
        confidence: float,
        top_words: List[Dict]
    ) -> str:
        """
        Generate explanation for a risky clause.
        
        Args:
            clause: The clause text
            risk_type: Type of risk detected
            confidence: Model confidence (0-1)
            top_words: Top influential words from attention (not used in templates)
        
        Returns:
            User-friendly explanation
        """
        return self._get_explanation(risk_type)
    
    def _get_explanation(self, risk_type: str) -> str:
        """Get explanation template for risk type."""
        
        explanations = {
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
        
        return explanations.get(
            risk_type,
            'This clause contains terms that may limit your legal rights, protections, or ability to seek compensation if something goes wrong.'
        )
