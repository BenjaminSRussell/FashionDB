#!/usr/bin/env python3
"""
Web Scraping Tester
Tests scraping on various fashion websites to see what works.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

# Add scrapers to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import GenericBlogScraper, GenericForumScraper, test_scraper


def load_url_analysis(reports_dir: Path) -> Dict:
    """Load URL analysis results."""
    analysis_path = reports_dir / "url_analysis.json"

    if not analysis_path.exists():
        print(f"Error: Run extract_urls.py first to generate {analysis_path}")
        sys.exit(1)

    with open(analysis_path, 'r') as f:
        return json.load(f)


def get_test_urls(url_data_path: Path, targets: List[Dict], max_per_domain: int = 3) -> Dict[str, List[str]]:
    """
    Get sample URLs for each target domain.
    """
    if not url_data_path.exists():
        print(f"Error: URL data not found at {url_data_path}")
        return {}

    with open(url_data_path, 'r') as f:
        url_data = json.load(f)

    # Group URLs by domain
    domain_urls = {}
    for url in url_data.keys():
        for target in targets:
            domain = target['domain']
            if domain in url.lower():
                if domain not in domain_urls:
                    domain_urls[domain] = []
                if len(domain_urls[domain]) < max_per_domain:
                    domain_urls[domain].append(url)

    return domain_urls


def test_blog_scraping(domain: str, urls: List[str]) -> Dict:
    """Test scraping blog/article URLs."""
    print(f"\n{'=' * 60}")
    print(f"Testing Blog Scraper: {domain}")
    print(f"{'=' * 60}")

    scraper = GenericBlogScraper(domain, f"https://{domain}")
    results = {
        'domain': domain,
        'type': 'blog',
        'tested_urls': len(urls),
        'successful': 0,
        'failed': 0,
        'samples': []
    }

    for url in urls:
        success = test_scraper(scraper, url)
        if success:
            results['successful'] += 1
        else:
            results['failed'] += 1

        results['samples'].append({
            'url': url,
            'success': success
        })

    return results


def test_forum_scraping(domain: str, urls: List[str]) -> Dict:
    """Test scraping forum URLs."""
    print(f"\n{'=' * 60}")
    print(f"Testing Forum Scraper: {domain}")
    print(f"{'=' * 60}")

    scraper = GenericForumScraper(domain, f"https://{domain}")
    results = {
        'domain': domain,
        'type': 'forum',
        'tested_urls': len(urls),
        'successful': 0,
        'failed': 0,
        'samples': []
    }

    for url in urls:
        success = test_scraper(scraper, url)
        if success:
            results['successful'] += 1
        else:
            results['failed'] += 1

        results['samples'].append({
            'url': url,
            'success': success
        })

    return results


def generate_scraping_report(test_results: List[Dict], output_path: Path):
    """Generate report on scraping test results."""

    report = []
    report.append("=" * 80)
    report.append("WEB SCRAPING TEST RESULTS")
    report.append("=" * 80)
    report.append("")

    # Summary
    total_domains = len(test_results)
    total_urls = sum(r['tested_urls'] for r in test_results)
    total_successful = sum(r['successful'] for r in test_results)
    total_failed = sum(r['failed'] for r in test_results)

    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Domains tested: {total_domains}")
    report.append(f"URLs tested: {total_urls}")
    report.append(f"Successful scrapes: {total_successful} ({total_successful/total_urls*100:.1f}%)")
    report.append(f"Failed scrapes: {total_failed} ({total_failed/total_urls*100:.1f}%)")
    report.append("")

    # Per-domain results
    report.append("RESULTS BY DOMAIN")
    report.append("-" * 80)
    report.append(f"{'Domain':<40} {'Type':<10} {'Success Rate':<15} {'Status'}")
    report.append("-" * 80)

    for result in test_results:
        success_rate = result['successful'] / result['tested_urls'] * 100 if result['tested_urls'] > 0 else 0
        status = "✓ Ready" if success_rate > 50 else "✗ Needs work"

        report.append(
            f"{result['domain']:<40} {result['type']:<10} "
            f"{result['successful']}/{result['tested_urls']} ({success_rate:.0f}%)"
            f"{'':<5} {status}"
        )

    report.append("")

    # Recommendations
    report.append("RECOMMENDATIONS")
    report.append("-" * 80)

    ready_domains = [r for r in test_results if r['successful'] / r['tested_urls'] > 0.5]
    needs_work = [r for r in test_results if r['successful'] / r['tested_urls'] <= 0.5]

    if ready_domains:
        report.append("\nREADY TO SCRAPE (>50% success rate):")
        for r in ready_domains:
            report.append(f"  ✓ {r['domain']} ({r['type']})")

    if needs_work:
        report.append("\nNEEDS CUSTOM SCRAPER (<50% success rate):")
        for r in needs_work:
            report.append(f"  ✗ {r['domain']} ({r['type']}) - Build domain-specific scraper")

    report.append("")

    # Next steps
    report.append("NEXT STEPS")
    report.append("-" * 80)
    report.append("1. For 'Ready' domains: Use generic scrapers in production")
    report.append("2. For 'Needs work' domains: Build custom scrapers")
    report.append("3. See scrapers/ directory for implementation templates")
    report.append("4. Review individual sample scrapes for quality")
    report.append("")
    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open(output_path, 'w') as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")

    # Save detailed JSON
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"Detailed results saved to: {json_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / "reports"
    url_data_path = reports_dir / "extracted_urls_full.json"
    output_path = reports_dir / "scraping_test_results.txt"

    print("=" * 80)
    print("WEB SCRAPING TEST SUITE")
    print("=" * 80)

    # Load URL analysis
    print("\nLoading URL analysis...")
    analysis = load_url_analysis(reports_dir)

    # Get top scraping targets (excluding reddit, images, social)
    targets = [
        t for t in analysis['scraping_targets'][:20]
        if t['category'] not in ['reddit', 'image_host', 'social_media']
    ]

    print(f"Found {len(targets)} domains to test")

    # Get test URLs for each domain
    print("Gathering test URLs...")
    domain_urls = get_test_urls(url_data_path, targets, max_per_domain=2)

    print(f"Will test {len(domain_urls)} domains with {sum(len(urls) for urls in domain_urls.values())} URLs")

    # Run tests
    test_results = []

    for domain, urls in list(domain_urls.items())[:10]:  # Test first 10 domains
        # Determine type
        target = next(t for t in targets if t['domain'] == domain)
        category = target['category']

        if category == 'forum':
            results = test_forum_scraping(domain, urls)
        else:  # blog, website, other
            results = test_blog_scraping(domain, urls)

        test_results.append(results)

    # Generate report
    print("\n" + "=" * 80)
    print("Generating report...")
    generate_scraping_report(test_results, output_path)

    print("\n✓ Scraping tests complete!")


if __name__ == "__main__":
    main()
