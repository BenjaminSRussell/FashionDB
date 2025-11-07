#!/usr/bin/env python3
"""
Query Effectiveness Analyzer
Analyzes which search queries are most effective for finding fashion rules.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def load_data(data_path: Path) -> Dict:
    """Load the Reddit fashion data."""
    print(f"Loading data from {data_path}...")
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_queries(queries_path: Path) -> Dict:
    """Load search queries."""
    with open(queries_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_query_matches(data: Dict, queries: Dict) -> List[Tuple[str, Dict]]:
    """
    Analyze which queries would match which posts.
    Returns list of (query, metrics) tuples.
    """
    results = []

    for category, query_list in queries.items():
        print(f"\nAnalyzing category: {category}")

        for query in query_list:
            # Simple matching: check if query terms appear in title or selftext
            query_lower = query.lower()
            query_terms = set(query_lower.split())

            matches = []
            total_score = 0
            total_comments = 0

            for subreddit, posts in data.items():
                for post in posts:
                    title = post.get('title', '').lower()
                    selftext = post.get('selftext', '').lower()
                    combined = f"{title} {selftext}"

                    # Check if query matches
                    if any(term in combined for term in query_terms):
                        matches.append(post)
                        total_score += post.get('score', 0)
                        total_comments += len(post.get('comments', []))

            if matches:
                metrics = {
                    'query': query,
                    'category': category,
                    'matches': len(matches),
                    'avg_score': total_score / len(matches),
                    'avg_comments': total_comments / len(matches),
                    'total_engagement': total_score + total_comments
                }
                results.append((query, metrics))

    return results


def generate_report(results: List[Tuple[str, Dict]], output_path: Path):
    """Generate effectiveness report."""

    # Sort by total engagement
    results.sort(key=lambda x: x[1]['total_engagement'], reverse=True)

    report = []
    report.append("=" * 80)
    report.append("QUERY EFFECTIVENESS ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary statistics
    total_queries = len(results)
    queries_with_matches = sum(1 for _, m in results if m['matches'] > 0)
    queries_no_matches = total_queries - queries_with_matches

    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Total queries analyzed: {total_queries}")
    report.append(f"Queries with matches: {queries_with_matches}")
    report.append(f"Queries with no matches: {queries_no_matches}")
    report.append(f"Match rate: {queries_with_matches/total_queries*100:.1f}%")
    report.append("")

    # Top performers
    report.append("TOP 50 PERFORMING QUERIES")
    report.append("-" * 80)
    report.append(f"{'Rank':<6} {'Matches':<8} {'Avg Score':<10} {'Avg Comments':<13} Query")
    report.append("-" * 80)

    for rank, (query, metrics) in enumerate(results[:50], 1):
        report.append(
            f"{rank:<6} {metrics['matches']:<8} "
            f"{metrics['avg_score']:<10.1f} {metrics['avg_comments']:<13.1f} "
            f"{query[:60]}"
        )

    report.append("")
    report.append("=" * 80)

    # Bottom performers
    report.append("BOTTOM 50 PERFORMING QUERIES (Consider removing)")
    report.append("-" * 80)
    report.append(f"{'Rank':<6} {'Matches':<8} {'Avg Score':<10} {'Avg Comments':<13} Query")
    report.append("-" * 80)

    for rank, (query, metrics) in enumerate(results[-50:], len(results)-49):
        report.append(
            f"{rank:<6} {metrics['matches']:<8} "
            f"{metrics['avg_score']:<10.1f} {metrics['avg_comments']:<13.1f} "
            f"{query[:60]}"
        )

    report.append("")
    report.append("=" * 80)

    # Category breakdown
    report.append("PERFORMANCE BY CATEGORY")
    report.append("-" * 80)

    category_stats = defaultdict(lambda: {'queries': 0, 'matches': 0, 'engagement': 0})
    for query, metrics in results:
        cat = metrics['category']
        category_stats[cat]['queries'] += 1
        category_stats[cat]['matches'] += metrics['matches']
        category_stats[cat]['engagement'] += metrics['total_engagement']

    for category, stats in sorted(category_stats.items(),
                                   key=lambda x: x[1]['engagement'],
                                   reverse=True):
        avg_matches = stats['matches'] / stats['queries']
        report.append(f"{category:<40} Queries: {stats['queries']:<4} "
                     f"Avg Matches: {avg_matches:<6.1f}")

    report.append("")
    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")

    # Save detailed JSON results
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([{'query': q, 'metrics': m} for q, m in results],
                  f, indent=2, ensure_ascii=False)
    print(f"Detailed JSON saved to: {json_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    # Paths
    data_path = base_dir / "data" / "reddit_fashion_data.json"
    queries_path = base_dir / "RedditDB" / "search_queries.json"
    output_path = base_dir / "reports" / "query_effectiveness.txt"

    # Create reports directory
    output_path.parent.mkdir(exist_ok=True)

    # Check files exist
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}", file=sys.stderr)
        sys.exit(1)

    if not queries_path.exists():
        print(f"Error: Queries file not found at {queries_path}", file=sys.stderr)
        sys.exit(1)

    # Load and analyze
    data = load_data(data_path)
    queries = load_queries(queries_path)

    print(f"\nLoaded {len(data)} subreddits")
    total_posts = sum(len(posts) for posts in data.values())
    print(f"Total posts: {total_posts}")

    total_queries = sum(len(q_list) for q_list in queries.values())
    print(f"Total queries: {total_queries}")

    print("\nStarting analysis...")
    results = analyze_query_matches(data, queries)

    print(f"\nAnalyzed {len(results)} queries")
    generate_report(results, output_path)


if __name__ == "__main__":
    main()
