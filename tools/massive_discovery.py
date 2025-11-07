#!/usr/bin/env python3
"""Massive URL discovery - find hundreds of fashion rule articles."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Rule-focused search terms
RULE_SEARCHES = [
    # Direct rules
    "fashion rules for men",
    "style rules every man should know",
    "menswear dos and donts",
    "fashion dos and donts men",
    "style mistakes to avoid",
    "what not to wear men",
    "how to dress better men",
    "style tips for men",

    # Specific items
    "how to wear a suit",
    "suit rules men",
    "dress shirt rules",
    "tie dos and donts",
    "jeans fit guide",
    "how to match colors men",
    "shoe matching rules",
    "belt matching rules",

    # Occasions
    "business casual dos and donts",
    "smart casual rules",
    "formal wear rules men",
    "date night outfit rules",
    "wedding guest attire men",
    "job interview outfit rules",

    # Fit
    "how should a suit fit",
    "pants fit guide men",
    "shirt fit rules",
    "jacket fit guide",
    "proper fit menswear",

    # Color
    "color matching rules men",
    "what colors go together menswear",
    "color combinations men",
    "navy suit what to wear",
    "gray suit combinations",

    # Mistakes
    "biggest style mistakes men",
    "fashion mistakes to avoid",
    "common menswear errors",
    "what not to do style",
]

# Target sites (expanded)
FASHION_SITES = [
    # Existing high performers
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

    # New high-quality sites
    'artofmanliness.com',
    'realmenrealstyle.com',
    'fashionbeans.com',
    'thetrendspotter.net',
    'themodestman.com',
    'mensfashioner.com',
    'thedarkknot.com',
    'blacklapel.com',
    'propercloth.com',
    'bespokeedge.com',
    'manofmany.com',
    'dmarge.com',
    'gq.com',
    'esquire.com',
    'menshealth.com',
    'askmen.com',
    'complex.com',
    'insidehook.com',
    'gear-patrol.com',
    'uncrate.com',
    'coolmaterial.com',
    'hiconsumption.com',
    'manmadediy.com',
    'fashionbeans.com',
    'thetrendspotter.net',
    'styleandthetailor.com',
    'kinowear.com',
    'acontinuouslean.com',
    'afinetoothcomb.co.uk',
]

def generate_massive_batch():
    """Generate hundreds of search queries."""
    queries = []

    # Rule-focused searches
    for search_term in RULE_SEARCHES:
        queries.append({
            'query': search_term,
            'type': 'rule_search',
            'focus': 'dos_and_donts'
        })

    # Site-specific rule searches
    for site in FASHION_SITES[:30]:
        queries.extend([
            {
                'query': f'site:{site} "dos and donts" OR "rules" OR "guide"',
                'type': 'site_rules',
                'site': site
            },
            {
                'query': f'site:{site} "how to" OR "style tips"',
                'type': 'site_howto',
                'site': site
            },
            {
                'query': f'site:{site} "fit guide" OR "should fit"',
                'type': 'site_fit',
                'site': site
            },
        ])

    # Topic + rule combinations
    topics = [
        'suit', 'jacket', 'blazer', 'shirt', 'tie', 'pants', 'jeans',
        'shoes', 'boots', 'sneakers', 'dress shoes', 'loafers'
    ]

    for topic in topics:
        queries.extend([
            {'query': f'{topic} dos and donts men', 'type': 'topic_rules', 'topic': topic},
            {'query': f'{topic} rules men', 'type': 'topic_rules', 'topic': topic},
            {'query': f'{topic} style guide men', 'type': 'topic_guide', 'topic': topic},
            {'query': f'how to wear {topic}', 'type': 'topic_howto', 'topic': topic},
        ])

    return queries


def main():
    """Generate massive URL discovery batch."""
    queries = generate_massive_batch()

    output = {
        'total_queries': len(queries),
        'focus': 'FASHION RULES AND DOS AND DONTS',
        'target_sites': len(FASHION_SITES),
        'sites': FASHION_SITES,
        'search_queries': queries
    }

    output_file = BASE_DIR / 'data' / 'massive_url_discovery.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"MASSIVE URL DISCOVERY")
    print(f"=" * 80)
    print(f"Total queries: {len(queries)}")
    print(f"Target sites: {len(FASHION_SITES)}")
    print(f"Focus: FASHION RULES AND DOS AND DONTS")
    print()
    print(f"Query types:")
    types = {}
    for q in queries:
        types[q['type']] = types.get(q['type'], 0) + 1
    for qtype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {qtype}: {count}")
    print()
    print(f"Saved to: {output_file}")
    print()
    print("Sample queries:")
    for q in queries[:10]:
        print(f"  {q['query']}")


if __name__ == "__main__":
    main()
