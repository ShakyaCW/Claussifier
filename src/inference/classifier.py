"""
Claussifier Inference Module

This module provides the RiskClassifier class for classifying legal clauses
using the trained BERT model with optimized thresholds.
"""

import torch
import json
import os
from pathlib import Path
from typing import Dict, List, Union, Optional
from transformers import BertTokenizer, BertForSequenceClassification
import warnings

warnings.filterwarnings('ignore')


class RiskClassifier:
    """
    Legal clause risk classifier using trained BERT model.
    
    Usage:
        classifier = RiskClassifier(model_dir="path/to/model")
        result = classifier.classify("Your clause text here")
    """
    
    # Risk category names (must match training order)
    LABEL_NAMES = [
        "Limitation of liability",
        "Unilateral termination",
        "Unilateral change",
        "Content removal",
        "Contract by using",
        "Choice of law",
        "Jurisdiction",
        "Arbitration"
    ]
    
    def __init__(
        self,
        model_dir: str,
        thresholds_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Initialize the risk classifier.
        
        Args:
            model_dir: Path to the trained model directory
            thresholds_path: Path to optimal_thresholds.json (optional)
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        self.model_dir = Path(model_dir)
        
        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        print(f"Loading model on device: {self.device}")
        
        # Load model and tokenizer
        self._load_model()
        
        # Load optimal thresholds
        self._load_thresholds(thresholds_path)
        
        print("✓ RiskClassifier initialized successfully!")
    
    def _load_model(self):
        """Load BERT model and tokenizer."""
        try:
            self.tokenizer = BertTokenizer.from_pretrained(self.model_dir)
            
            # Load model with eager attention implementation (required for attention output)
            self.model = BertForSequenceClassification.from_pretrained(
                self.model_dir,
                attn_implementation='eager'  # Required for output_attentions
            )
            
            # Enable attention output for XAI
            self.model.config.output_attentions = True
            
            self.model.to(self.device)
            self.model.eval()
            print(f"✓ Model loaded from: {self.model_dir}")
            print(f"  - Attention implementation: eager")
            print(f"  - Output attentions: {self.model.config.output_attentions}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def _load_thresholds(self, thresholds_path: Optional[str] = None):
        """Load optimal thresholds from JSON file."""
        if thresholds_path is None:
            # Try to find optimal_thresholds.json in results directory
            results_dir = self.model_dir.parent.parent / "results"
            thresholds_path = results_dir / "optimal_thresholds.json"
        
        if os.path.exists(thresholds_path):
            with open(thresholds_path, 'r') as f:
                config = json.load(f)
                self.thresholds = config['optimal_thresholds']
            print(f"✓ Loaded optimal thresholds from: {thresholds_path}")
        else:
            # Use default threshold of 0.5 for all classes
            self.thresholds = [0.5] * len(self.LABEL_NAMES)
            print("⚠ Using default thresholds (0.5) - optimal thresholds not found")
    
    def classify(
        self,
        clause: str,
        return_all_scores: bool = False
    ) -> Dict:
        """
        Classify a single legal clause.
        
        Args:
            clause: The legal clause text to classify
            return_all_scores: If True, return scores for all categories
        
        Returns:
            Dictionary containing classification results:
            {
                'clause': str,
                'is_risky': bool,
                'risks_detected': List[Dict],
                'safe_categories': List[str],
                'all_scores': List[Dict] (if return_all_scores=True)
            }
        """
        # Tokenize input
        encoding = self.tokenizer(
            clause,
            add_special_tokens=True,
            max_length=512,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.sigmoid(logits).cpu().numpy()[0]
        
        # Apply optimal thresholds
        risks_detected = []
        safe_categories = []
        all_scores = []
        
        for idx, (label, prob, threshold) in enumerate(
            zip(self.LABEL_NAMES, probs, self.thresholds)
        ):
            score_info = {
                'risk_type': label,
                'confidence': float(prob),
                'threshold': threshold,
                'predicted': prob >= threshold
            }
            
            if return_all_scores:
                all_scores.append(score_info)
            
            if prob >= threshold:
                risks_detected.append({
                    'risk_type': label,
                    'confidence': float(prob),
                    'threshold': threshold
                })
            else:
                safe_categories.append(label)
        
        # Build result
        result = {
            'clause': clause,
            'is_risky': len(risks_detected) > 0,
            'risks_detected': sorted(
                risks_detected,
                key=lambda x: x['confidence'],
                reverse=True
            ),
            'safe_categories': safe_categories
        }
        
        if return_all_scores:
            result['all_scores'] = sorted(
                all_scores,
                key=lambda x: x['confidence'],
                reverse=True
            )
        
        return result
    
    def classify_with_attention(
        self,
        clause: str,
        return_all_scores: bool = False
    ) -> Dict:
        """
        Classify a single legal clause with attention-based explanations.
        
        Args:
            clause: The legal clause text to classify
            return_all_scores: If True, return scores for all categories
        
        Returns:
            Dictionary containing classification results + attention explanation:
            {
                'clause': str,
                'is_risky': bool,
                'risks_detected': List[Dict],
                'safe_categories': List[str],
                'attention_explanation': Dict (XAI data)
            }
        """
        # Import here to avoid circular dependency
        from .attention_explainer import AttentionExplainer
        
        # Tokenize input
        encoding = self.tokenizer(
            clause,
            add_special_tokens=True,
            max_length=512,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # Get predictions WITH attention output
        with torch.no_grad():
            outputs = self.model(
                input_ids,
                attention_mask=attention_mask,
                output_attentions=True  # KEY: Enable attention output
            )
            logits = outputs.logits
            probs = torch.sigmoid(logits).cpu().numpy()[0]
            attentions = outputs.attentions  # Tuple of attention tensors
        
        # Apply optimal thresholds (same as classify method)
        risks_detected = []
        safe_categories = []
        all_scores = []
        
        for idx, (label, prob, threshold) in enumerate(
            zip(self.LABEL_NAMES, probs, self.thresholds)
        ):
            score_info = {
                'risk_type': label,
                'confidence': float(prob),
                'threshold': threshold,
                'predicted': prob >= threshold
            }
            
            if return_all_scores:
                all_scores.append(score_info)
            
            if prob >= threshold:
                risks_detected.append({
                    'risk_type': label,
                    'confidence': float(prob),
                    'threshold': threshold
                })
            else:
                safe_categories.append(label)
        
        # Extract attention explanation
        explainer = AttentionExplainer()
        attention_explanation = explainer.explain_prediction(
            input_ids=input_ids,
            attentions=attentions,
            tokenizer=self.tokenizer,
            top_k=10
        )
        
        # Build result with attention
        result = {
            'clause': clause,
            'is_risky': len(risks_detected) > 0,
            'risks_detected': sorted(
                risks_detected,
                key=lambda x: x['confidence'],
                reverse=True
            ),
            'safe_categories': safe_categories,
            'attention_explanation': attention_explanation  # NEW: XAI data
        }
        
        if return_all_scores:
            result['all_scores'] = sorted(
                all_scores,
                key=lambda x: x['confidence'],
                reverse=True
            )
        
        return result
    
    def classify_batch(
        self,
        clauses: List[str],
        batch_size: int = 16,
        return_all_scores: bool = False
    ) -> List[Dict]:
        """
        Classify multiple clauses in batches.
        
        Args:
            clauses: List of clause texts to classify
            batch_size: Number of clauses to process at once
            return_all_scores: If True, return scores for all categories
        
        Returns:
            List of classification results (same format as classify())
        """
        results = []
        
        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i + batch_size]
            
            for clause in batch:
                result = self.classify(clause, return_all_scores=return_all_scores)
                results.append(result)
        
        return results
    
    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        return {
            'model_name': 'BERT Risk Detector',
            'model_type': 'bert-base-uncased',
            'num_labels': len(self.LABEL_NAMES),
            'label_names': self.LABEL_NAMES,
            'thresholds': self.thresholds,
            'device': str(self.device),
            'model_dir': str(self.model_dir)
        }


# Example usage
if __name__ == "__main__":
    # Example: Load model and classify a clause
    
    # Path to your model (update this!)
    MODEL_DIR = "path/to/models/legalbert_final_model"
    
    # Initialize classifier
    classifier = RiskClassifier(model_dir=MODEL_DIR)
    
    # Example clauses
    test_clauses = [
        "We may terminate your account at any time without prior notice.",
        "This agreement shall be governed by the laws of Delaware.",
        "We are not liable for any damages arising from use of this service.",
        "You agree to binding arbitration for all disputes."
    ]
    
    # Classify each clause
    print("\n" + "="*80)
    print("CLASSIFICATION RESULTS")
    print("="*80)
    
    for clause in test_clauses:
        result = classifier.classify(clause)
        
        print(f"\nClause: {clause}")
        print(f"Risky: {result['is_risky']}")
        
        if result['risks_detected']:
            print("Risks detected:")
            for risk in result['risks_detected']:
                print(f"  • {risk['risk_type']}: {risk['confidence']:.2%} confidence")
        else:
            print("No risks detected ✓")
        
        print("-" * 80)
