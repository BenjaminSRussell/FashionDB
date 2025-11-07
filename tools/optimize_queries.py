#!/usr/bin/env python3
"""
Query Optimizer
Generates an optimized set of search queries from the current 1,588.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def load_queries(path: Path) -> Dict[str, List[str]]:
    """Load existing queries."""
    with open(path, 'r') as f:
        return json.load(f)


def deduplicate_queries(queries: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Remove duplicate queries across categories."""
    seen = set()
    deduplicated = defaultdict(list)

    for category, query_list in queries.items():
        for query in query_list:
            query_lower = query.lower().strip()
            if query_lower not in seen:
                seen.add(query_lower)
                deduplicated[category].append(query)

    return dict(deduplicated)


def extract_query_patterns(queries: Dict[str, List[str]]) -> Dict[str, int]:
    """Extract common query patterns."""
    patterns = defaultdict(int)

    for query_list in queries.values():
        for query in query_list:
            # Extract pattern keywords
            if "what to wear" in query.lower():
                patterns["what_to_wear"] += 1
            if "how to" in query.lower():
                patterns["how_to"] += 1
            if "simple outfit" in query.lower():
                patterns["outfit_formula"] += 1
            if "accessories" in query.lower():
                patterns["accessories"] += 1
            if "color" in query.lower():
                patterns["color"] += 1
            if "fit" in query.lower():
                patterns["fit"] += 1
            if "layering" in query.lower():
                patterns["layering"] += 1
            if "rule" in query.lower():
                patterns["rules"] += 1

    return dict(patterns)


def generate_core_queries() -> List[str]:
    """Generate high-impact core queries."""
    return [
        # Fundamentals
        'flair:guide fit',
        'flair:guide color',
        'flair:guide proportion',
        'flair:guide basics',
        'flair:guide beginner',

        # Fit & tailoring
        'suit fit guide',
        'jacket fit shoulders',
        'pants fit rise break',
        'shirt fit sleeve length',
        'how clothes should fit',

        # Color coordination
        'color coordination',
        'color theory menswear',
        'matching colors outfit',
        'navy and black together',
        'what colors go together',

        # Dress codes
        'business casual',
        'smart casual',
        'black tie',
        'cocktail attire',
        'dress code explained',

        # Common scenarios
        'first date outfit',
        'wedding guest attire',
        'interview outfit',
        'office wear',
        'casual friday',

        # Garment-specific
        'jeans guide',
        'suit guide',
        'dress shirt guide',
        'sneakers guide',
        'boots guide',

        # Style fundamentals
        'building a wardrobe',
        'capsule wardrobe',
        'versatile pieces',
        'wardrobe essentials',
        'timeless style',

        # Common problems
        'outfit mistakes',
        'fashion mistakes to avoid',
        'style rules',
        'when to break rules',
        'common fit issues',

        # Proportions
        'proportion guide',
        'layering guide',
        'body type dressing',
        'height and style',
        'silhouette guide',
    ]


def generate_scenario_queries() -> Dict[str, List[str]]:
    """Generate scenario-based queries."""
    return {
        "workplace": [
            'office outfit',
            'business casual guide',
            'professional attire',
            'work wardrobe',
            'dress code office',
        ],
        "social": [
            'first date outfit',
            'wedding guest what to wear',
            'dinner party outfit',
            'meeting parents outfit',
            'casual date outfit',
        ],
        "formal": [
            'black tie guide',
            'suit rules',
            'cocktail attire men',
            'formal wear guide',
            'tuxedo vs suit',
        ],
        "casual": [
            'casual outfit ideas',
            'weekend wear',
            'smart casual guide',
            'streetwear basics',
            'everyday style',
        ],
        "seasonal": [
            'summer outfit',
            'winter layering',
            'fall style',
            'spring transition',
            'weather appropriate',
        ],
    }


def generate_reddit_advanced_queries() -> List[str]:
    """Generate advanced Reddit search queries with operators."""
    return [
        # Use flair filters
        'flair:guide style',
        'flair:discussion fit',
        'flair:advice color',

        # Combine terms
        'fit AND proportion',
        'color AND coordination',
        'suit AND tailoring',

        # Time-based
        'guide OR tips selftext:yes',

        # High engagement
        'style rules',
        'fashion mistakes',
        'outfit advice',

        # Specific topics with operators
        'title:guide (fit OR color OR style)',
        'title:rules menswear',
        'selftext:proportion selftext:body',
    ]


def optimize_queries(original: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Create optimized query set."""
    optimized = {}

    # Core queries (highest priority)
    optimized['core_fundamentals'] = generate_core_queries()

    # Scenario queries
    scenario_queries = generate_scenario_queries()
    optimized.update(scenario_queries)

    # Advanced Reddit queries
    optimized['advanced_reddit_queries'] = generate_reddit_advanced_queries()

    # Extract top queries from each original category
    for category, query_list in original.items():
        # Take top 5 from each category (as examples)
        # In practice, you'd rank by effectiveness metrics
        top_queries = query_list[:5]
        if top_queries and category not in optimized:
            optimized[f'original_{category}_top'] = top_queries

    return optimized


def generate_report(original: Dict, deduplicated: Dict, optimized: Dict, output_path: Path):
    """Generate optimization report."""
    report = []
    report.append("=" * 80)
    report.append("QUERY OPTIMIZATION REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary
    original_count = sum(len(q) for q in original.values())
    dedup_count = sum(len(q) for q in deduplicated.values())
    optimized_count = sum(len(q) for q in optimized.values())

    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Original query count: {original_count}")
    report.append(f"After deduplication: {dedup_count}")
    report.append(f"Optimized query count: {optimized_count}")
    report.append(f"Reduction: {original_count - optimized_count} queries ({(1-optimized_count/original_count)*100:.1f}%)")
    report.append("")

    # Pattern analysis
    patterns = extract_query_patterns(original)
    report.append("QUERY PATTERNS IN ORIGINAL SET")
    report.append("-" * 80)
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:15]:
        report.append(f"{pattern:<30} {count} queries")
    report.append("")

    # Categories
    report.append("OPTIMIZED QUERY CATEGORIES")
    report.append("-" * 80)
    for category, queries in optimized.items():
        report.append(f"{category:<40} {len(queries)} queries")
    report.append("")

    # Sample queries
    report.append("SAMPLE CORE QUERIES (First 20)")
    report.append("-" * 80)
    core = optimized.get('core_fundamentals', [])
    for i, query in enumerate(core[:20], 1):
        report.append(f"{i:2}. {query}")
    report.append("")

    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open(output_path, 'w') as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    # Paths
    original_path = base_dir / "RedditDB" / "search_queries.json"
    optimized_path = base_dir / "RedditDB" / "search_queries_optimized.json"
    report_path = base_dir / "reports" / "query_optimization.txt"

    # Create reports directory
    report_path.parent.mkdir(exist_ok=True)

    # Check file exists
    if not original_path.exists():
        print(f"Error: Queries file not found at {original_path}", file=sys.stderr)
        sys.exit(1)

    print("Loading original queries...")
    original = load_queries(original_path)

    print("Deduplicating queries...")
    deduplicated = deduplicate_queries(original)

    print("Generating optimized query set...")
    optimized = optimize_queries(deduplicated)

    print("Generating report...")
    generate_report(original, deduplicated, optimized, report_path)

    # Save optimized queries
    with open(optimized_path, 'w') as f:
        json.dump(optimized, f, indent=2, ensure_ascii=False)

    print(f"\nOptimized queries saved to: {optimized_path}")
    print(f"Original count: {sum(len(q) for q in original.values())}")
    print(f"Optimized count: {sum(len(q) for q in optimized.values())}")


if __name__ == "__main__":
    main()
