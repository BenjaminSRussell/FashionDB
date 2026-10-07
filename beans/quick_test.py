#!/usr/bin/env python3
"""Quick test to verify extraction works with Data Analysis proven code."""

import sys
sys.path.insert(0, '../Data Analysis/src')

from fashion_rule_extractor import extract_rule_from_post, Config
from mlx_lm import load

# Test text
test_text = """
Fashion Rules Every Man Should Know:

1. Never button the bottom button of a suit jacket
2. Black shoes don't go with brown belts
3. Match your belt leather to your shoe leather
4. The tie should reach the middle of your belt buckle
5. Ensure shirt cuffs extend half an inch beyond jacket sleeves
"""

print("="*80)
print("TESTING PROVEN EXTRACTION LOGIC")
print("="*80)

# Load model
print("\nLoading model...")
config = Config()
model, tokenizer = load(config.model_name)
print("Model loaded!")

# Create fake post
post = {
    "title": "Essential Fashion Rules",
    "selftext": test_text,
    "comments": [],
    "post_id": "test1"
}

# Extract
print("\nExtracting rules...")
result = extract_rule_from_post(model, tokenizer, post, config)

if result["success"]:
    extraction = result["extraction"]
    print(f"\nSuccess!")
    print(f"Has Fashion Rule: {extraction.get('has_fashion_rule', False)}")
    print(f"Category: {extraction.get('category', 'unknown')}")
    print(f"Confidence: {extraction.get('confidence', 'unknown')}")

    if extraction.get('rules'):
        print(f"\nExtracted {len(extraction['rules'])} rules:")
        for i, rule in enumerate(extraction['rules'], 1):
            print(f"  {i}. {rule}")
    else:
        print("\nNo rules extracted")
else:
    print(f"\nFailed: {result.get('error', 'Unknown error')}")

print("\n" + "="*80)
print("TEST COMPLETE - If you see rules above, extraction is working!")
print("="*80)
