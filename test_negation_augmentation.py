"""
Test script for negation augmentation logic.
Tests negation patterns on a small sample from the LexGLUE unfair_tos dataset.
"""

from datasets import load_dataset
import re


def negate_clause(clause):
    """
    Apply negation to a risky clause.
    Returns (negated_clause, pattern_used) or (None, None) if negation doesn't make sense.
    """
    clause_lower = clause.lower()
    
    # Pattern 1: Modal verb "may"
    if ' may ' in clause_lower:
        negated = re.sub(r'\bmay\b', 'may not', clause, count=1, flags=re.IGNORECASE)
        return negated, "Modal: may → may not"
    
    # Pattern 2: Modal verb "can"
    elif ' can ' in clause_lower:
        negated = re.sub(r'\bcan\b', 'cannot', clause, count=1, flags=re.IGNORECASE)
        return negated, "Modal: can → cannot"
    
    # Pattern 3: Modal verb "will"
    elif ' will ' in clause_lower:
        negated = re.sub(r'\bwill\b', 'will not', clause, count=1, flags=re.IGNORECASE)
        return negated, "Modal: will → will not"
    
    # Pattern 4: Modal verb "shall"
    elif ' shall ' in clause_lower:
        negated = re.sub(r'\bshall\b', 'shall not', clause, count=1, flags=re.IGNORECASE)
        return negated, "Modal: shall → shall not"
    
    # Pattern 5: "reserve the right"
    elif 'reserve the right' in clause_lower:
        negated = re.sub(r'reserve the right', 'do not reserve the right', clause, count=1, flags=re.IGNORECASE)
        return negated, "Phrase: reserve the right → do not reserve the right"
    
    # Pattern 6: "has the right"
    elif 'has the right' in clause_lower:
        negated = re.sub(r'has the right', 'does not have the right', clause, count=1, flags=re.IGNORECASE)
        return negated, "Phrase: has the right → does not have the right"
    
    # Pattern 7: "have the right"
    elif 'have the right' in clause_lower:
        negated = re.sub(r'have the right', 'do not have the right', clause, count=1, flags=re.IGNORECASE)
        return negated, "Phrase: have the right → do not have the right"
    
    # Pattern 8: "is/are entitled to"
    elif 'is entitled to' in clause_lower or 'are entitled to' in clause_lower:
        negated = re.sub(r'is entitled to', 'is not entitled to', clause, count=1, flags=re.IGNORECASE)
        negated = re.sub(r'are entitled to', 'are not entitled to', negated, count=1, flags=re.IGNORECASE)
        return negated, "Phrase: entitled to → not entitled to"
    
    # Pattern 9: "agree to" / "agrees to"
    elif 'agree to' in clause_lower or 'agrees to' in clause_lower:
        negated = re.sub(r'agree to', 'do not agree to', clause, count=1, flags=re.IGNORECASE)
        negated = re.sub(r'agrees to', 'does not agree to', negated, count=1, flags=re.IGNORECASE)
        return negated, "Phrase: agree to → do not agree to"
    
    return None, None


def test_negation_augmentation(num_samples=20):
    """
    Test negation augmentation on a small sample from the dataset.
    """
    print("=" * 100)
    print("NEGATION AUGMENTATION TEST")
    print("=" * 100)
    print("\nLoading dataset from Hugging Face...")
    
    # Load dataset
    dataset = load_dataset("lex_glue", "unfair_tos")
    train_data = dataset['train']
    
    # Get label names
    label_names = train_data.features['labels'].feature.names
    
    print(f"✓ Dataset loaded: {len(train_data)} training examples")
    print(f"✓ Risk categories: {label_names}")
    print("\n" + "=" * 100)
    print(f"TESTING NEGATION ON {num_samples} RISKY CLAUSES")
    print("=" * 100)
    
    successful_negations = 0
    failed_negations = 0
    
    # Test on first num_samples risky clauses
    for i, example in enumerate(train_data):
        if successful_negations >= num_samples:
            break
        
        # Only process clauses with at least one risk label
        if len(example['labels']) > 0:
            original_clause = example['text']
            original_labels = [label_names[idx] for idx in example['labels']]
            
            # Try to negate
            negated_clause, pattern = negate_clause(original_clause)
            
            if negated_clause:
                successful_negations += 1
                print(f"\n{'─' * 100}")
                print(f"EXAMPLE {successful_negations}")
                print(f"{'─' * 100}")
                print(f"Pattern Used: {pattern}")
                print(f"\nOriginal Risks: {', '.join(original_labels)}")
                print(f"\nORIGINAL CLAUSE:")
                print(f"  {original_clause}")
                print(f"\nNEGATED CLAUSE (Safe):")
                print(f"  {negated_clause}")
            else:
                failed_negations += 1
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"✓ Successful negations: {successful_negations}")
    print(f"✗ Failed negations (no pattern matched): {failed_negations}")
    print(f"Success rate: {successful_negations / (successful_negations + failed_negations) * 100:.1f}%")
    
    print("\n" + "=" * 100)
    print("PATTERN COVERAGE ANALYSIS")
    print("=" * 100)
    
    # Analyze which patterns are most common
    pattern_counts = {}
    for example in train_data:
        if len(example['labels']) > 0:
            _, pattern = negate_clause(example['text'])
            if pattern:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    
    print("\nPattern frequency in dataset:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} clauses")
    
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)
    print("1. Review the negated clauses above to verify they make grammatical sense")
    print("2. Check if the negations truly reverse the risk (risky → safe)")
    print("3. If satisfied, proceed with full augmentation for model retraining")
    print("=" * 100)


if __name__ == "__main__":
    test_negation_augmentation(num_samples=20)
