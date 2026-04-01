"""
Attention-based Explainer for BERT Risk Classifier

This module extracts and processes BERT attention weights to provide
explainable AI (XAI) insights into model predictions.
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional


class AttentionExplainer:
    """Extract and process BERT attention weights for explanations."""
    
    @staticmethod
    def aggregate_attention(attentions: Tuple) -> np.ndarray:
        """
        Aggregate attention across all layers and heads.
        
        Args:
            attentions: Tuple of (batch, heads, seq_len, seq_len) tensors
        
        Returns:
            Aggregated attention matrix (seq_len, seq_len)
        """
        # Check if attentions is None or empty
        if attentions is None or len(attentions) == 0:
            raise ValueError("Attentions is None or empty. Make sure model.config.output_attentions=True")
        
        # Filter out None values
        valid_attentions = [att for att in attentions if att is not None]
        if len(valid_attentions) == 0:
            raise ValueError("All attention tensors are None")
        
        # Stack all layers: (layers, batch, heads, seq, seq)
        attention_stack = torch.stack(valid_attentions)
        
        # Average across layers and heads: (seq, seq)
        # Using mean across layers (0) and heads (2), squeeze batch dim (1)
        avg_attention = attention_stack.mean(dim=(0, 2)).squeeze(0)
        
        return avg_attention.cpu().numpy()
    
    @staticmethod
    def get_token_importance(
        attention_matrix: np.ndarray,
        method: str = 'cls'
    ) -> np.ndarray:
        """
        Calculate importance score for each token.
        
        Args:
            attention_matrix: (seq_len, seq_len) attention weights
            method: 'cls' (attention to [CLS]) or 'mean' (average attention)
        
        Returns:
            Importance scores for each token
        """
        if method == 'cls':
            # Attention from [CLS] token (index 0) to all other tokens
            # This shows what the model focused on for classification
            importance = attention_matrix[0, :]
        elif method == 'mean':
            # Average attention received by each token
            importance = attention_matrix.mean(axis=0)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return importance
    
    def explain_prediction(
        self,
        input_ids: torch.Tensor,
        attentions: Tuple,
        tokenizer,
        top_k: int = 10
    ) -> Dict:
        """
        Generate explanation from attention weights.
        
        Args:
            input_ids: Token IDs from tokenizer
            attentions: Attention weights from BERT
            tokenizer: BERT tokenizer for decoding
            top_k: Number of top words to return
        
        Returns:
            {
                'tokens': List[str],
                'importance_scores': List[float],
                'top_words': List[Dict],
                'heatmap_data': List[Dict]
            }
        """
        # 1. Aggregate attention
        attention_matrix = self.aggregate_attention(attentions)
        
        # 2. Get token importance
        importance_scores = self.get_token_importance(attention_matrix, method='cls')
        
        # 3. Convert token IDs to words
        tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
        
        # 4. Filter out special tokens and padding
        valid_indices = [
            i for i, token in enumerate(tokens)
            if token not in ['[CLS]', '[SEP]', '[PAD]']
        ]
        
        valid_tokens = [tokens[i] for i in valid_indices]
        valid_scores = [importance_scores[i] for i in valid_indices]
        
        # 5. Merge subword tokens (##)
        merged_words, merged_scores = self._merge_subwords(
            valid_tokens, valid_scores
        )
        
        # Post-process: Zero out common stopwords and legal boilerplate
        stopwords = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
            'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
            'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
            'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'may',
            # Legal boilerplate and fillers
            'hereby', 'herein', 'therein', 'whereby', 'hereinafter', 'shall', 'whereas', 'thereto', 'therefore'
        }
        
        for i in range(len(merged_words)):
            if merged_words[i].lower() in stopwords:
                merged_scores[i] = 0.0
        
        # 6. Get top-k most important words (filter out punctuation and zeroed stopwords)
        if len(merged_scores) > 0:
            # Define punctuation and special tokens to filter out
            punctuation = {'.', ',', '!', '?', ';', ':', '-', '–', '—', '(', ')', '[', ']', 
                          '{', '}', '"', "'", '`', '/', '\\', '|', '@', '#', '$', '%', 
                          '^', '&', '*', '+', '=', '<', '>', '~'}
            
            # Create list of (index, word, score) tuples, filtering punctuation and zero-scores
            word_score_pairs = [
                (i, merged_words[i], merged_scores[i])
                for i in range(len(merged_words))
                if merged_words[i] not in punctuation and len(merged_words[i]) > 1 and merged_scores[i] > 0.0
            ]
            
            # Sort by score and take top-k
            word_score_pairs.sort(key=lambda x: x[2], reverse=True)
            top_pairs = word_score_pairs[:top_k]
            
            top_words = [
                {
                    'word': word,
                    'importance': float(score),
                    'position': int(idx)  # Convert numpy int64 to Python int
                }
                for idx, word, score in top_pairs
            ]
        else:
            top_words = []
        
        # 7. Create heatmap data (for visualization)
        max_score = max(merged_scores) if merged_scores and max(merged_scores) > 0 else 1.0
        
        # Reuse the same punctuation set
        punctuation = {'.', ',', '!', '?', ';', ':', '-', '–', '—', '(', ')', '[', ']', 
                      '{', '}', '"', "'", '`', '/', '\\', '|', '@', '#', '$', '%', 
                      '^', '&', '*', '+', '=', '<', '>', '~'}
        
        heatmap_data = [
            {
                'word': word,
                'importance': float(score),
                'normalized': float(score / max_score) if max_score > 0 else 0.0
            }
            for word, score in zip(merged_words, merged_scores)
            if word not in punctuation and len(word) > 1
        ]
        
        return {
            'tokens': merged_words,
            'importance_scores': [float(s) for s in merged_scores],
            'top_words': top_words,
            'heatmap_data': heatmap_data
        }
    
    @staticmethod
    def _merge_subwords(
        tokens: List[str],
        scores: List[float]
    ) -> Tuple[List[str], List[float]]:
        """
        Merge BERT subword tokens (e.g., 'dis', '##claim' -> 'disclaim').
        
        Args:
            tokens: List of tokens (may include ## subwords)
            scores: Corresponding importance scores
        
        Returns:
            Tuple of (merged_words, merged_scores)
        """
        merged_words = []
        merged_scores = []
        
        current_word = ""
        current_score = 0.0
        subword_count = 0
        
        for token, score in zip(tokens, scores):
            if token.startswith('##'):
                # Continuation of previous word
                current_word += token[2:]  # Remove ##
                current_score += score
                subword_count += 1
            else:
                # New word
                if current_word:
                    merged_words.append(current_word)
                    merged_scores.append(current_score / subword_count)
                
                current_word = token
                current_score = score
                subword_count = 1
        
        # Add last word
        if current_word:
            merged_words.append(current_word)
            merged_scores.append(current_score / subword_count)
        
        return merged_words, merged_scores
