"""
Test if the model can load with the new attention configuration
"""

import sys
sys.path.append('.')

print("=" * 80)
print("Testing Model Loading with Attention Support")
print("=" * 80)

try:
    from src.inference.classifier import RiskClassifier
    
    print("\n1. Importing RiskClassifier... ✓")
    
    print("\n2. Loading model...")
    classifier = RiskClassifier(model_dir="src/models/legalbert_final_model")
    
    print("✓ Model loaded successfully!")
    print(f"   - Device: {classifier.device}")
    print(f"   - Model config output_attentions: {classifier.model.config.output_attentions}")
    
    print("\n3. Testing classification with attention...")
    test_clause = "We are not liable for any damages."
    
    result = classifier.classify_with_attention(test_clause)
    
    print("✓ Classification successful!")
    print(f"   - Is risky: {result['is_risky']}")
    print(f"   - Has attention_explanation: {'attention_explanation' in result}")
    
    if 'attention_explanation' in result:
        attention = result['attention_explanation']
        print(f"   - Number of tokens: {len(attention['tokens'])}")
        print(f"   - Top words: {len(attention['top_words'])}")
        
        print("\n4. Top 3 influential words:")
        for i, word in enumerate(attention['top_words'][:3], 1):
            print(f"   {i}. '{word['word']}' → {word['importance']:.4f}")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED!")
    print("=" * 80)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    print("\n" + "=" * 80)
    import traceback
    traceback.print_exc()
    print("=" * 80)
