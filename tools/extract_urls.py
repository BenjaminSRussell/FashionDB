#!/usr/bin/env python3
"""
URL Extractor and Analyzer
Extracts all URLs from Reddit data to discover external fashion content sources.
This is the "beans" - finding article data and other sources to scrape!
"""

import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse


def extract_urls_from_text(text: str) -> List[str]:
    """Extract all URLs from text."""
    # Match URLs with http/https
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def categorize_url(url: str) -> Tuple[str, str]:
    """
    Categorize URL by domain and type.
    Returns (domain, category)
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except (ValueError, AttributeError):
        # Handle malformed URLs
        return "malformed", "other"

    if not domain:
        return "unknown", "other"

    # Remove www prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    # Categorize by domain
    if 'reddit.com' in domain or 'redd.it' in domain:
        return domain, 'reddit'
    elif 'imgur.com' in domain or 'i.imgur.com' in domain:
        return domain, 'image_host'
    elif 'youtube.com' in domain or 'youtu.be' in domain:
        return domain, 'video'
    elif 'instagram.com' in domain:
        return domain, 'social_media'
    elif 'twitter.com' in domain or 'x.com' in domain:
        return domain, 'social_media'
    elif any(x in domain for x in ['styleforum', 'style-forum']):
        return domain, 'forum'
    elif any(x in domain for x in ['blog', 'wordpress', 'medium', 'substack']):
        return domain, 'blog'
    elif any(x in domain for x in ['.com', '.net', '.org', '.io']):
        return domain, 'website'
    else:
        return domain, 'other'


def extract_all_urls(data: Dict) -> Dict[str, List[Dict]]:
    """
    Extract all URLs from Reddit data.
    Returns dict of {url: [contexts]}
    """
    url_data = defaultdict(list)

    print("Extracting URLs from posts and comments...")
    total_posts = 0
    total_comments = 0

    for subreddit, posts in data.items():
        for post in posts:
            total_posts += 1

            # Extract from post URL
            post_url = post.get('url', '')
            if post_url and not post_url.startswith('https://reddit.com'):
                url_data[post_url].append({
                    'source': 'post_url',
                    'subreddit': subreddit,
                    'post_id': post.get('post_id'),
                    'post_title': post.get('title', '')[:100],
                    'post_score': post.get('score', 0)
                })

            # Extract from post selftext
            selftext = post.get('selftext', '')
            if selftext:
                for url in extract_urls_from_text(selftext):
                    url_data[url].append({
                        'source': 'post_body',
                        'subreddit': subreddit,
                        'post_id': post.get('post_id'),
                        'post_title': post.get('title', '')[:100],
                        'post_score': post.get('score', 0)
                    })

            # Extract from comments
            for comment in post.get('comments', []):
                total_comments += 1
                body = comment.get('body', '')
                if body:
                    for url in extract_urls_from_text(body):
                        url_data[url].append({
                            'source': 'comment',
                            'subreddit': subreddit,
                            'post_id': post.get('post_id'),
                            'comment_id': comment.get('comment_id'),
                            'comment_score': comment.get('score', 0)
                        })

    print(f"Processed {total_posts} posts and {total_comments} comments")
    print(f"Found {len(url_data)} unique URLs")

    return dict(url_data)


def analyze_urls(url_data: Dict) -> Dict:
    """Analyze URL patterns and generate insights."""

    # Count by domain
    domain_counts = Counter()
    domain_categories = {}
    domain_scores = defaultdict(list)

    for url, contexts in url_data.items():
        domain, category = categorize_url(url)
        domain_counts[domain] += len(contexts)
        domain_categories[domain] = category

        # Track scores for quality assessment
        for ctx in contexts:
            score = ctx.get('post_score', 0) or ctx.get('comment_score', 0)
            domain_scores[domain].append(score)

    # Calculate domain metrics
    domain_metrics = []
    for domain, count in domain_counts.items():
        scores = domain_scores[domain]
        avg_score = sum(scores) / len(scores) if scores else 0

        domain_metrics.append({
            'domain': domain,
            'mentions': count,
            'category': domain_categories[domain],
            'avg_score': avg_score,
            'quality_score': count * (1 + avg_score / 100)  # Combined metric
        })

    # Sort by quality score
    domain_metrics.sort(key=lambda x: x['quality_score'], reverse=True)

    # Category breakdown
    category_counts = Counter(domain_categories.values())

    return {
        'domain_metrics': domain_metrics,
        'category_counts': dict(category_counts),
        'total_urls': len(url_data),
        'total_mentions': sum(domain_counts.values())
    }


def identify_scraping_targets(analysis: Dict, min_mentions: int = 10) -> List[Dict]:
    """
    Identify high-value domains to scrape.
    """
    targets = []

    for domain_info in analysis['domain_metrics']:
        domain = domain_info['domain']
        mentions = domain_info['mentions']
        category = domain_info['category']

        # Skip certain categories
        if category in ['reddit', 'image_host', 'social_media']:
            continue

        # Must have minimum mentions
        if mentions < min_mentions:
            continue

        # Calculate priority score
        priority_score = domain_info['quality_score']

        targets.append({
            'domain': domain,
            'mentions': mentions,
            'avg_score': domain_info['avg_score'],
            'category': category,
            'priority': priority_score,
            'scraping_feasibility': 'unknown'  # To be assessed
        })

    return targets


def generate_url_report(analysis: Dict, url_data: Dict, output_path: Path):
    """Generate comprehensive URL analysis report."""

    report = []
    report.append("=" * 80)
    report.append("URL EXTRACTION AND ANALYSIS REPORT")
    report.append("Finding External Fashion Content Sources (The 'Beans'!)")
    report.append("=" * 80)
    report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Total unique URLs found: {analysis['total_urls']}")
    report.append(f"Total URL mentions: {analysis['total_mentions']}")
    report.append(f"Avg mentions per URL: {analysis['total_mentions'] / analysis['total_urls']:.1f}")
    report.append("")

    # Category breakdown
    report.append("URL CATEGORIES")
    report.append("-" * 80)
    for category, count in sorted(analysis['category_counts'].items(),
                                   key=lambda x: x[1], reverse=True):
        report.append(f"{category:<20} {count:>5} domains")
    report.append("")

    # Top domains overall
    report.append("TOP 50 DOMAINS BY MENTIONS")
    report.append("-" * 80)
    report.append(f"{'Rank':<6} {'Mentions':<10} {'Avg Score':<12} {'Category':<15} Domain")
    report.append("-" * 80)

    for rank, domain_info in enumerate(analysis['domain_metrics'][:50], 1):
        report.append(
            f"{rank:<6} {domain_info['mentions']:<10} "
            f"{domain_info['avg_score']:<12.1f} {domain_info['category']:<15} "
            f"{domain_info['domain']}"
        )

    report.append("")

    # Scraping targets
    targets = identify_scraping_targets(analysis, min_mentions=5)

    report.append("HIGH-VALUE SCRAPING TARGETS (Excluding Reddit/Images/Social)")
    report.append("-" * 80)
    report.append(f"{'Rank':<6} {'Mentions':<10} {'Category':<15} Domain")
    report.append("-" * 80)

    for rank, target in enumerate(targets[:30], 1):
        report.append(
            f"{rank:<6} {target['mentions']:<10} "
            f"{target['category']:<15} {target['domain']}"
        )

    report.append("")

    # Category-specific recommendations
    report.append("RECOMMENDED SCRAPING PRIORITIES BY CATEGORY")
    report.append("-" * 80)

    # Forums
    forum_targets = [t for t in targets if t['category'] == 'forum']
    if forum_targets:
        report.append("\nFORUMS (High Priority):")
        for t in forum_targets[:5]:
            report.append(f"  - {t['domain']} ({t['mentions']} mentions)")

    # Blogs
    blog_targets = [t for t in targets if t['category'] == 'blog']
    if blog_targets:
        report.append("\nBLOGS:")
        for t in blog_targets[:10]:
            report.append(f"  - {t['domain']} ({t['mentions']} mentions)")

    # Websites
    website_targets = [t for t in targets if t['category'] == 'website'][:15]
    if website_targets:
        report.append("\nWEBSITES:")
        for t in website_targets:
            report.append(f"  - {t['domain']} ({t['mentions']} mentions)")

    # Videos
    video_targets = [t for t in targets if t['category'] == 'video'][:5]
    if video_targets:
        report.append("\nVIDEO SOURCES:")
        for t in video_targets:
            report.append(f"  - {t['domain']} ({t['mentions']} mentions)")

    report.append("")
    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")

    # Save detailed JSON data
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis': analysis,
            'scraping_targets': targets[:50]
        }, f, indent=2, ensure_ascii=False)

    print(f"Detailed JSON saved to: {json_path}")

    # Save full URL data
    url_data_path = output_path.parent / 'extracted_urls_full.json'
    with open(url_data_path, 'w', encoding='utf-8') as f:
        json.dump(url_data, f, indent=2, ensure_ascii=False)

    print(f"Full URL data saved to: {url_data_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    # Paths
    data_path = base_dir / "data" / "reddit_fashion_data.json"
    output_path = base_dir / "reports" / "url_analysis.txt"

    # Create reports directory
    output_path.parent.mkdir(exist_ok=True)

    # Check file exists
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}", file=sys.stderr)
        sys.exit(1)

    print("Loading Reddit data...")
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} subreddits")

    # Extract URLs
    url_data = extract_all_urls(data)

    # Analyze
    print("\nAnalyzing URL patterns...")
    analysis = analyze_urls(url_data)

    # Generate report
    print("\nGenerating report...")
    generate_url_report(analysis, url_data, output_path)

    print("\n✓ URL extraction complete!")
    print("\nNext steps:")
    print("1. Review reports/url_analysis.txt for top sources")
    print("2. Run tools/build_scrapers.py to create scrapers for top domains")
    print("3. Test scraping with tools/test_scraping.py")


if __name__ == "__main__":
    main()
