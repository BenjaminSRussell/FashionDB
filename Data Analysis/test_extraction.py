"""Test the fashion rule extraction on a few sample posts."""

import json
from pathlib import Path
from src.fashion_rule_extractor import (
    load_posts,
    extract_rule_from_post,
    Config,
)
from mlx_lm import load

# Load config and model
config = Config()
print("Loading model...")
model, tokenizer = load(config.model_name)
print("Model loaded!\n")

# Load posts
print("Loading posts...")
posts = load_posts(config.input_path)
print(f"Loaded {len(posts)} posts\n")

# Test on first 5 posts
print("="*80)
print("TESTING EXTRACTION ON FIRST 5 POSTS")
print("="*80)

for i, post in enumerate(posts[:5], 1):
    title = post.get("title", "")[:70]
    print(f"\nTest {i}/5: {title}...")
    print("-" * 80)

    result = extract_rule_from_post(model, tokenizer, post, config)

    if result["success"]:
        extraction = result["extraction"]
        print(f"✓ Has Fashion Rule: {extraction.get('has_fashion_rule', False)}")
        print(f"  Category: {extraction.get('category', 'unknown')}")
        print(f"  Confidence: {extraction.get('confidence', 'unknown')}")
        if extraction.get('rules'):
            print(f"  Rules Extracted:")
            for rule in extraction['rules']:
                print(f"    - {rule}")
        else:
            print(f"  No specific rules extracted")
    else:
        print(f"✗ Error: {result.get('error', 'Unknown error')}")
        if result.get('raw_response'):
            print(f"  Raw response: {result['raw_response'][:150]}...")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
