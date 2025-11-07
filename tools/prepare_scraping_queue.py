#!/usr/bin/env python3
"""
Prepare Scraping Queue
Combines curated sites + Reddit-discovered URLs into organized scraping queue.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_reddit_urls(url_data_path: Path) -> dict:
    """Load URLs extracted from Reddit."""
    with open(url_data_path, 'r') as f:
        return json.load(f)


def load_curated_sites(curated_path: Path) -> list:
    """Load curated site configurations."""
    with open(curated_path, 'r') as f:
        return json.load(f)


def organize_urls_by_domain(url_data: dict) -> dict:
    """Organize URLs by domain."""
    domain_urls = defaultdict(list)

    for url, contexts in url_data.items():
        # Skip image and video URLs
        if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif', '.jpeg', '.mp4', '.webm']):
            continue

        # Skip reddit URLs
        if 'reddit.com' in url.lower() or 'redd.it' in url.lower():
            continue

        # Extract domain
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')

            if domain:
                domain_urls[domain].append({
                    'url': url,
                    'mentions': len(contexts),
                    'avg_score': sum(c.get('post_score', 0) or c.get('comment_score', 0) for c in contexts) / len(contexts) if contexts else 0
                })
        except:
            continue

    return dict(domain_urls)


def create_scraping_queue(curated_sites: list, reddit_urls: dict, output_path: Path):
    """
    Create organized scraping queue combining curated + discovered sources.
    """
    queue = {
        'curated_sites': [],
        'reddit_discovered': [],
        'statistics': {}
    }

    # Add curated sites (priority scraping)
    curated_domains = set()
    for site in curated_sites:
        domain = site['domain']
        curated_domains.add(domain)

        queue['curated_sites'].append({
            'name': site['name'],
            'domain': domain,
            'urls': site['urls'],
            'priority': site['priority'],
            'delay': site['delay'],
            'scraping_notes': site['scraping_analysis'],
            'source': 'curated'
        })

    # Add Reddit-discovered URLs (for sites not in curated list)
    high_value_domains = [
        'styleforum.net',
        'putthison.com',
        'dappered.com',
        'theshoesnobblog.com',
        'streetxsprezza.wordpress.com',
        'nstarleather.wordpress.com',
        'medium.com',
        'theperfectgentleman.co.za',
        'glenpalmerstyle.com',
        'asuitablewardrobe.com',
        'themodestguy.com'
    ]

    for domain in high_value_domains:
        if domain not in curated_domains and domain in reddit_urls:
            urls_info = reddit_urls[domain]
            # Sort by mentions
            urls_info.sort(key=lambda x: x['mentions'], reverse=True)

            queue['reddit_discovered'].append({
                'domain': domain,
                'urls': [u['url'] for u in urls_info[:50]],  # Top 50 URLs
                'total_mentions': sum(u['mentions'] for u in urls_info),
                'source': 'reddit_discovery'
            })

    # Statistics
    queue['statistics'] = {
        'curated_sites': len(queue['curated_sites']),
        'reddit_discovered': len(queue['reddit_discovered']),
        'total_curated_urls': sum(len(s['urls']) for s in queue['curated_sites']),
        'total_discovered_urls': sum(len(s['urls']) for s in queue['reddit_discovered']),
        'total_sources': len(queue['curated_sites']) + len(queue['reddit_discovered'])
    }

    # Save queue
    with open(output_path, 'w') as f:
        json.dump(queue, f, indent=2)

    return queue


def generate_queue_report(queue: dict, output_path: Path):
    """Generate human-readable report of scraping queue."""
    report = []
    report.append("=" * 80)
    report.append("SCRAPING QUEUE REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary
    stats = queue['statistics']
    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Curated sites: {stats['curated_sites']}")
    report.append(f"Reddit-discovered sites: {stats['reddit_discovered']}")
    report.append(f"Total sources: {stats['total_sources']}")
    report.append(f"Total URLs to scrape: {stats['total_curated_urls'] + stats['total_discovered_urls']}")
    report.append("")

    # Curated sites
    report.append("CURATED SITES (Priority)")
    report.append("-" * 80)
    report.append(f"{'Priority':<10} {'Name':<40} {'URLs'}")
    report.append("-" * 80)

    for site in sorted(queue['curated_sites'], key=lambda x: x['priority'], reverse=True):
        report.append(f"{site['priority']:<10} {site['name']:<40} {len(site['urls'])}")

    report.append("")

    # Reddit-discovered
    report.append("REDDIT-DISCOVERED SITES")
    report.append("-" * 80)
    report.append(f"{'Domain':<40} {'URLs':<10} {'Mentions'}")
    report.append("-" * 80)

    for site in sorted(queue['reddit_discovered'], key=lambda x: x['total_mentions'], reverse=True):
        report.append(f"{site['domain']:<40} {len(site['urls']):<10} {site['total_mentions']}")

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
    reddit_urls_path = base_dir / "reports" / "extracted_urls_full.json"
    curated_sites_path = base_dir / "scrapers" / "curated_sites.json"
    queue_output = base_dir / "data" / "scraping_queue.json"
    report_output = base_dir / "reports" / "scraping_queue.txt"

    # Create reports directory
    report_output.parent.mkdir(exist_ok=True)

    # Check files exist
    if not reddit_urls_path.exists():
        print(f"Error: Reddit URLs not found. Run extract_urls.py first.")
        sys.exit(1)

    if not curated_sites_path.exists():
        print(f"Error: Curated sites config not found.")
        sys.exit(1)

    print("Loading data...")
    reddit_url_data = load_reddit_urls(reddit_urls_path)
    curated_sites = load_curated_sites(curated_sites_path)

    print("Organizing URLs by domain...")
    reddit_urls_by_domain = organize_urls_by_domain(reddit_url_data)

    print("Creating scraping queue...")
    queue = create_scraping_queue(curated_sites, reddit_urls_by_domain, queue_output)

    print("Generating report...")
    generate_queue_report(queue, report_output)

    print(f"\n✓ Scraping queue created!")
    print(f"  Queue file: {queue_output}")
    print(f"  Report: {report_output}")


if __name__ == "__main__":
    main()
