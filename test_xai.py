"""
Test script for XAI attention-based explanations
"""

import sys
sys.path.append('.')

from src.inference.classifier import RiskClassifier

# Initialize classifier
print("Loading model...")
classifier = RiskClassifier(model_dir="src/models/legalbert_final_model")

# Test clause
test_clause = "We disclaim all liability for any damages arising from your use of the service."

print(f"\nTest Clause: {test_clause}\n")
print("="*80)

# Classify with attention
print("\nClassifying with attention...")
result = classifier.classify_with_attention(test_clause)

# Display results
print(f"\nRisky: {result['is_risky']}")
print(f"\nRisks Detected:")
for risk in result['risks_detected']:
    print(f"  • {risk['risk_type']}: {risk['confidence']:.2%}")

# Display attention explanation
if 'attention_explanation' in result:
    attention = result['attention_explanation']
    
    print(f"\n🔍 XAI Explanation:")
    print(f"\nTop {len(attention['top_words'])} Influential Words:")
    for i, word_info in enumerate(attention['top_words'][:5], 1):
        print(f"  {i}. '{word_info['word']}' → {word_info['importance']:.4f}")
    
    print(f"\nHeatmap Data (first 10 words):")
    for item in attention['heatmap_data'][:10]:
        bar_length = int(item['normalized'] * 30)
        bar = '█' * bar_length
        print(f"  {item['word']:15s} {bar} {item['importance']:.4f}")

print("\n" + "="*80)
print("✓ Test complete!")
