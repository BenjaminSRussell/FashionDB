#!/usr/bin/env python3
"""Validate JSON articles - check quality and completeness."""

import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
ARTICLES_FILE = BASE_DIR / "data" / "scraped_articles.json"

# Fashion terms
FASHION_TERMS = {
    'suit', 'jacket', 'blazer', 'pants', 'shirt', 'tie', 'shoes', 'boots',
    'denim', 'jeans', 'style', 'fashion', 'outfit', 'wardrobe', 'fit',
    'casual', 'formal', 'preppy', 'classic', 'navy', 'gray', 'black'
}


def validate_article(article):
    """Return quality metrics for article."""
    body = article.get("body", "")
    word_count = article.get("word_count", 0)

    # Count fashion terms
    body_lower = body.lower()
    fashion_terms = sum(1 for term in FASHION_TERMS if term in body_lower)

    # Check completeness
    truncated = body and not body.strip().endswith(('.', '!', '?'))

    # Quality score (0-100)
    score = 0
    if word_count >= 1000: score += 30
    elif word_count >= 500: score += 20
    elif word_count >= 300: score += 10

    score += min(fashion_terms, 30)  # Max 30 pts for fashion terms
    if re.search(r'\bhow to\b|\bshould\b|\bwear\b', body_lower): score += 10

    if truncated: score *= 0.7

    return {
        "word_count": word_count,
        "fashion_terms": fashion_terms,
        "truncated": truncated,
        "quality_score": int(score)
    }


def main():
    """Validate all articles."""
    if not ARTICLES_FILE.exists():
        print(f"No articles found: {ARTICLES_FILE}")
        return

    with open(ARTICLES_FILE, 'r') as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"Validating {len(articles)} articles...\n")

    # Validate each
    metrics = []
    for article in articles:
        m = validate_article(article)
        metrics.append({**article, **m})

    # Stats
    total = len(metrics)
    high_quality = sum(1 for m in metrics if m["quality_score"] >= 70)
    complete = sum(1 for m in metrics if not m["truncated"])
    avg_words = sum(m["word_count"] for m in metrics) / total if total else 0

    print(f"Total articles: {total}")
    print(f"High quality (70+): {high_quality} ({high_quality/total*100:.1f}%)")
    print(f"Complete: {complete} ({complete/total*100:.1f}%)")
    print(f"Average words: {int(avg_words)}")
    print()

    # Top 5
    print("Top 5 articles:")
    top = sorted(metrics, key=lambda x: x["quality_score"], reverse=True)[:5]
    for i, m in enumerate(top, 1):
        print(f"{i}. [{m['quality_score']}] {m['title'][:60]}")
        print(f"   {m['word_count']} words | {m['url']}")

    # Save metrics
    output = BASE_DIR / "data" / "validation_metrics.json"
    with open(output, 'w') as f:
        json.dump({"articles": metrics, "summary": {
            "total": total,
            "high_quality": high_quality,
            "complete": complete,
            "avg_words": int(avg_words)
        }}, f, indent=2)

    print(f"\nMetrics saved to: {output}")


if __name__ == "__main__":
    main()
