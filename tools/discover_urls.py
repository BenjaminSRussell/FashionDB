#!/usr/bin/env python3
"""Advanced URL discovery - find fashion articles using multiple strategies."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse, urljoin
import time

BASE_DIR = Path(__file__).parent.parent

# Fashion topic keywords for discovery
FASHION_TOPICS = {
    'suits': ['suit', 'blazer', 'jacket', 'tailoring', 'bespoke', 'made to measure'],
    'shirts': ['dress shirt', 'oxford', 'OCBD', 'button down', 'polo'],
    'pants': ['pants', 'trousers', 'chinos', 'khakis', 'slacks'],
    'denim': ['jeans', 'denim', 'selvedge', 'raw denim', 'indigo'],
    'shoes': ['shoes', 'boots', 'loafers', 'oxfords', 'derby', 'sneakers'],
    'style_guides': ['style guide', 'how to dress', 'wardrobe essentials', 'fashion tips'],
    'color': ['color matching', 'color theory', 'color combinations', 'color coordination'],
    'fit': ['fit guide', 'how to fit', 'tailoring', 'alterations'],
    'occasions': ['business casual', 'smart casual', 'formal wear', 'date night'],
    'seasonal': ['fall fashion', 'winter style', 'summer outfits', 'spring wardrobe'],
    'brands': ['brand guide', 'brand review', 'brand comparison'],
    'budget': ['affordable', 'budget style', 'cheap', 'under $100']
}

# URL patterns that indicate fashion content
URL_PATTERNS = [
    r'/style[-_]?guide',
    r'/how[-_]to[-_]',
    r'/mens?[-_]fashion',
    r'/mens?[-_]style',
    r'/wardrobe',
    r'/outfit',
    r'/guide',
    r'/tips',
    r'/essentials',
    r'/fit[-_]guide',
    r'/color[-_]',
    r'/suit',
    r'/jacket',
    r'/shoes',
    r'/boots',
    r'/jeans',
    r'/denim',
]

# Sites to search
DISCOVERY_SITES = [
    # Already configured (high success)
    'putthison.com',
    'ivy-style.com',
    'dappered.com',
    'stitchdown.com',
    'primermagazine.com',
    'hespokestyle.com',
    'permanentstyle.com',
    'effortlessgent.com',
    'gentlemansgazette.com',
    'denimhunters.com',
    'heddels.com',
    'highsnobiety.com',
    'valetmag.com',

    # New sites to discover
    'artofmanliness.com',
    'bespokeedge.com',
    'styleandthetailor.com',
    'manofmany.com',
    'fashionbeans.com',
    'dmarge.com',
    'thetrendspotter.net',
    'themodestman.com',
    'mensfashioner.com',
    'thedarkknot.com',
    'blacklapel.com',
    'propercloth.com',
]

def generate_search_queries():
    """Generate search queries for each topic."""
    queries = []

    # Topic-based queries
    for topic, keywords in FASHION_TOPICS.items():
        for keyword in keywords[:2]:  # Top 2 per topic
            queries.append({
                'topic': topic,
                'query': f'{keyword} mens fashion guide',
                'keywords': [keyword]
            })

    # Site-specific queries
    for site in DISCOVERY_SITES[:10]:  # Top 10 sites
        queries.append({
            'topic': 'site_specific',
            'query': f'site:{site} style guide OR wardrobe OR outfit',
            'site': site
        })

    return queries


def filter_url(url):
    """Check if URL likely contains fashion content."""
    url_lower = url.lower()

    # Check patterns
    pattern_match = any(re.search(p, url_lower) for p in URL_PATTERNS)

    # Check keywords
    keyword_match = any(
        any(kw in url_lower for kw in keywords)
        for keywords in FASHION_TOPICS.values()
    )

    # Exclude bad patterns
    bad_patterns = [
        r'/tag/', r'/category/', r'/author/', r'/page/\d+',
        r'/amp/', r'/print/', r'/feed/', r'\.pdf$',
        r'/shop/', r'/cart/', r'/checkout/', r'/account/'
    ]
    bad_match = any(re.search(p, url_lower) for p in bad_patterns)

    return (pattern_match or keyword_match) and not bad_match


def score_url(url):
    """Score URL for relevance (0-100)."""
    score = 0
    url_lower = url.lower()

    # Pattern matches
    pattern_matches = sum(1 for p in URL_PATTERNS if re.search(p, url_lower))
    score += min(pattern_matches * 10, 40)

    # Keyword matches
    keyword_matches = sum(
        sum(1 for kw in keywords if kw in url_lower)
        for keywords in FASHION_TOPICS.values()
    )
    score += min(keyword_matches * 5, 30)

    # Domain reputation (from url_scraping_rules.json)
    domain = urlparse(url).netloc.replace('www.', '')
    if domain in DISCOVERY_SITES:
        score += 20

    # Depth penalty (prefer shorter URLs)
    depth = url.count('/')
    if depth <= 4:
        score += 10

    return min(score, 100)


def generate_discovery_batch():
    """Generate URL discovery batch file."""
    output = {
        'discovery_method': 'multi_strategy',
        'strategies': {
            'topic_keywords': list(FASHION_TOPICS.keys()),
            'url_patterns': URL_PATTERNS,
            'target_sites': DISCOVERY_SITES
        },
        'search_queries': generate_search_queries()[:50],  # Top 50
        'scoring_criteria': {
            'pattern_match': '10 points per pattern',
            'keyword_match': '5 points per keyword',
            'domain_reputation': '20 points',
            'url_depth': '10 points if shallow'
        }
    }

    output_file = BASE_DIR / 'data' / 'url_discovery_config.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"URL discovery config saved to: {output_file}")
    print(f"Generated {len(output['search_queries'])} search queries")
    print(f"Covering {len(FASHION_TOPICS)} topic categories")
    print(f"Targeting {len(DISCOVERY_SITES)} fashion sites")

    return output


def main():
    """Generate URL discovery configuration."""
    print("Advanced URL Discovery Configuration")
    print("=" * 80)
    print()

    config = generate_discovery_batch()

    print()
    print("Sample search queries:")
    for i, q in enumerate(config['search_queries'][:10], 1):
        print(f"{i}. {q['query']}")

    print()
    print("URL Scoring:")
    test_urls = [
        'https://putthison.com/style-guide-how-to-dress-well/',
        'https://example.com/mens-suit-fit-guide/',
        'https://example.com/tag/fashion/',  # Should score low
    ]

    for url in test_urls:
        score = score_url(url)
        filtered = filter_url(url)
        print(f"  {url}")
        print(f"    Score: {score}/100 | Pass filter: {filtered}")


if __name__ == "__main__":
    main()
