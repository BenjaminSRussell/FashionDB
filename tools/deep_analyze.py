#!/usr/bin/env python3
"""Deep article analysis - extract detailed fashion rules and patterns."""

import json
import re
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
ARTICLES_FILE = BASE_DIR / "data" / "scraped_articles.json"

# Fashion terminology
GARMENTS = {
    'suit', 'jacket', 'blazer', 'coat', 'overcoat', 'topcoat', 'trench',
    'shirt', 'dress shirt', 'oxford', 'polo', 'tee', 't-shirt',
    'pants', 'trousers', 'chinos', 'jeans', 'denim', 'slacks',
    'tie', 'necktie', 'bow tie', 'pocket square',
    'shoes', 'boots', 'loafers', 'oxfords', 'derby', 'brogues', 'sneakers',
    'sweater', 'cardigan', 'pullover', 'vest', 'waistcoat',
    'shorts', 'belt', 'socks', 'scarf', 'hat', 'cap'
}

MATERIALS = {
    'cotton', 'wool', 'linen', 'silk', 'cashmere', 'leather', 'suede',
    'denim', 'chambray', 'tweed', 'flannel', 'corduroy', 'velvet',
    'polyester', 'nylon', 'canvas', 'oxford cloth', 'poplin',
    'merino', 'alpaca', 'mohair', 'gabardine', 'herringbone'
}

COLORS = {
    'navy', 'black', 'white', 'gray', 'grey', 'charcoal', 'brown', 'tan',
    'khaki', 'olive', 'burgundy', 'maroon', 'blue', 'red', 'green',
    'beige', 'cream', 'camel', 'indigo', 'midnight'
}

STYLE_TERMS = {
    'casual', 'formal', 'business', 'smart casual', 'preppy', 'classic',
    'modern', 'vintage', 'streetwear', 'minimalist', 'tailored', 'bespoke',
    'slim fit', 'regular fit', 'relaxed fit', 'tapered'
}

BRANDS = {
    'brooks brothers', 'j crew', 'ralph lauren', 'gap', 'uniqlo',
    'patagonia', 'banana republic', 'zara', 'h&m', 'allen edmonds',
    'alden', 'red wing', 'levis', "levi's", 'wrangler', 'nudie',
    'a.p.c.', 'naked & famous', 'iron heart', 'viberg'
}

# Rule patterns
RULE_PATTERNS = {
    'always': r'\b(always|must|should always|never skip)\s+([^.!?]{10,80})',
    'never': r'\b(never|avoid|don\'t|do not)\s+([^.!?]{10,80})',
    'how_to': r'\bhow to\s+([^.!?]{10,80})',
    'when_to': r'\bwhen to\s+([^.!?]{10,80})',
    'pair_with': r'\b(pair|match|combine|wear)\s+\w+\s+with\s+([^.!?]{10,80})',
    'choose': r'\b(choose|select|pick|opt for)\s+([^.!?]{10,80})',
    'fit': r'\b(fit|should fit|fitting|fitted)\s+([^.!?]{10,80})',
    'color_match': r'\b(navy|black|brown|gray)\s+(pairs? with|goes? with|matches)\s+([^.!?]{10,80})'
}


def extract_rules(body):
    """Extract fashion rules from article body."""
    rules = []
    for rule_type, pattern in RULE_PATTERNS.items():
        matches = re.finditer(pattern, body, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) > 1:
                rule_text = match.group(2).strip()
            else:
                rule_text = match.group(1).strip()

            if len(rule_text) > 15:
                rules.append({
                    'type': rule_type,
                    'text': rule_text[:200]
                })
    return rules[:20]  # Limit to top 20 rules


def extract_mentions(body, terms):
    """Count term mentions in body."""
    body_lower = body.lower()
    mentions = {}
    for term in terms:
        count = body_lower.count(term.lower())
        if count > 0:
            mentions[term] = count
    return mentions


def extract_outfit_combos(body):
    """Extract outfit combinations mentioned."""
    combos = []

    # Pattern: "X with Y"
    pattern = r'(\w+(?:\s+\w+)?)\s+with\s+(\w+(?:\s+\w+)?)'
    matches = re.finditer(pattern, body.lower())

    for match in matches:
        item1, item2 = match.groups()
        if any(g in GARMENTS for g in [item1, item2]):
            combos.append(f"{item1} + {item2}")

    return list(set(combos))[:10]


def extract_price_ranges(body):
    """Extract price mentions."""
    prices = []
    pattern = r'\$(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)'
    matches = re.finditer(pattern, body)

    for match in matches:
        price = match.group(1).replace(',', '')
        try:
            prices.append(float(price))
        except:
            pass

    if prices:
        return {
            'min': int(min(prices)),
            'max': int(max(prices)),
            'avg': int(sum(prices) / len(prices)),
            'count': len(prices)
        }
    return None


def deep_analysis(article):
    """Perform deep analysis on article."""
    body = article.get('body', '')
    word_count = article.get('word_count', 0)

    # Extract everything
    rules = extract_rules(body)
    garment_mentions = extract_mentions(body, GARMENTS)
    material_mentions = extract_mentions(body, MATERIALS)
    color_mentions = extract_mentions(body, COLORS)
    style_mentions = extract_mentions(body, STYLE_TERMS)
    brand_mentions = extract_mentions(body, BRANDS)
    outfit_combos = extract_outfit_combos(body)
    price_info = extract_price_ranges(body)

    # Count total fashion content
    total_mentions = (
        sum(garment_mentions.values()) +
        sum(material_mentions.values()) +
        sum(color_mentions.values()) +
        sum(style_mentions.values())
    )

    # Calculate density (mentions per 100 words)
    density = (total_mentions / word_count * 100) if word_count > 0 else 0

    # Quality score
    score = 0
    if word_count >= 1500: score += 30
    elif word_count >= 1000: score += 25
    elif word_count >= 500: score += 15
    elif word_count >= 300: score += 10

    if len(rules) >= 10: score += 25
    elif len(rules) >= 5: score += 15
    elif len(rules) >= 3: score += 10

    if density > 10: score += 20
    elif density > 5: score += 10

    if len(garment_mentions) >= 5: score += 10
    if len(brand_mentions) >= 2: score += 5
    if price_info: score += 5

    truncated = body and not body.strip().endswith(('.', '!', '?', '"'))
    if truncated:
        score = int(score * 0.6)

    return {
        'word_count': word_count,
        'fashion_density': round(density, 2),
        'total_fashion_mentions': total_mentions,
        'rules_extracted': len(rules),
        'rules': rules,
        'garments': dict(sorted(garment_mentions.items(), key=lambda x: x[1], reverse=True)[:10]),
        'materials': dict(sorted(material_mentions.items(), key=lambda x: x[1], reverse=True)[:10]),
        'colors': dict(sorted(color_mentions.items(), key=lambda x: x[1], reverse=True)[:10]),
        'styles': dict(sorted(style_mentions.items(), key=lambda x: x[1], reverse=True)[:10]),
        'brands': brand_mentions,
        'outfit_combinations': outfit_combos,
        'price_info': price_info,
        'truncated': truncated,
        'quality_score': min(score, 100)
    }


def main():
    """Analyze all articles."""
    if not ARTICLES_FILE.exists():
        print(f"No articles: {ARTICLES_FILE}")
        return

    with open(ARTICLES_FILE, 'r') as f:
        data = json.load(f)

    articles = data.get('articles', [])
    print(f"Analyzing {len(articles)} articles...\n")

    # Analyze each
    analyzed = []
    for article in articles:
        analysis = deep_analysis(article)
        analyzed.append({**article, 'analysis': analysis})

    # Stats
    total = len(analyzed)
    high_quality = sum(1 for a in analyzed if a['analysis']['quality_score'] >= 70)
    with_rules = sum(1 for a in analyzed if a['analysis']['rules_extracted'] >= 5)
    total_rules = sum(a['analysis']['rules_extracted'] for a in analyzed)
    avg_density = sum(a['analysis']['fashion_density'] for a in analyzed) / total if total else 0

    print(f"Total articles: {total}")
    print(f"High quality (70+): {high_quality} ({high_quality/total*100:.1f}%)")
    print(f"Articles with 5+ rules: {with_rules} ({with_rules/total*100:.1f}%)")
    print(f"Total rules extracted: {total_rules}")
    print(f"Avg fashion density: {avg_density:.2f} mentions/100 words")
    print()

    # Top articles by rules
    print("Top 10 by rules extracted:")
    top_rules = sorted(analyzed, key=lambda x: x['analysis']['rules_extracted'], reverse=True)[:10]
    for i, a in enumerate(top_rules, 1):
        print(f"{i}. [{a['analysis']['rules_extracted']} rules] {a['title'][:60]}")
        print(f"   Score: {a['analysis']['quality_score']} | {a['word_count']} words | {a['domain']}")

    # Save
    output = BASE_DIR / "data" / "deep_analysis.json"
    with open(output, 'w') as f:
        json.dump({
            'articles': analyzed,
            'summary': {
                'total': total,
                'high_quality': high_quality,
                'with_rules': with_rules,
                'total_rules': total_rules,
                'avg_density': round(avg_density, 2)
            }
        }, f, indent=2)

    print(f"\nDeep analysis saved to: {output}")


if __name__ == "__main__":
    main()
