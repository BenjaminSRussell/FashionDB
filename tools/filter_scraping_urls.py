#!/usr/bin/env python3
"""
Filter Scraping URLs - Prepare Clean URL List
Filters Reddit-discovered URLs to remove images, malformed URLs, and bad sources.
Creates production-ready URL list for external website scraping.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse


class URLFilter:
    """Filters and prioritizes URLs for scraping."""

    # Domains to skip
    SKIP_DOMAINS = {
        'reddit.com',
        'redd.it',
        'youtube.com',
        'youtu.be',
        'instagram.com',
        'twitter.com',
        'facebook.com',
        'archive.org',  # Often blocks scrapers
        'web.archive.org',
    }

    # File extensions to skip
    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        '.mp4', '.webm', '.mov', '.avi',
        '.pdf',  # Need special handling
        '.zip', '.rar', '.tar', '.gz',
    }

    # CDN patterns to skip
    CDN_PATTERNS = [
        'cdn.', 'images.', 'img.', 'static.', 'media.',
        '/wp-content/uploads/',
        '/images/',
        '/img/',
    ]

    def __init__(self, urls_data_path: Path):
        self.urls_data_path = urls_data_path
        self.urls_data = self.load_urls()
        self.filtered_urls = []
        self.skip_reasons = defaultdict(int)

    def load_urls(self) -> Dict:
        """Load Reddit-discovered URLs."""
        with open(self.urls_data_path, 'r') as f:
            return json.load(f)

    def clean_url(self, url: str) -> str:
        """
        Clean URL by removing trailing markdown artifacts.
        """
        # Strip trailing punctuation from Reddit markdown
        url = url.rstrip(')')
        url = url.rstrip('),')
        url = url.rstrip('**')
        url = url.rstrip('!')
        url = url.rstrip('.')
        url = url.rstrip(']:')
        url = url.rstrip('](')

        return url

    def should_skip_url(self, url: str) -> tuple[bool, str]:
        """
        Check if URL should be skipped.
        Returns (should_skip, reason)
        """
        url_lower = url.lower()

        # Parse URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            path = parsed.path.lower()
        except:
            return True, 'parse_error'

        # Check domain
        if not domain:
            return True, 'no_domain'

        # Check skip domains
        for skip_domain in self.SKIP_DOMAINS:
            if skip_domain in domain:
                return True, f'skip_domain_{skip_domain.replace(".", "_")}'

        # Check file extensions
        for ext in self.SKIP_EXTENSIONS:
            if path.endswith(ext):
                return True, f'file_extension_{ext[1:]}'

        # Check CDN patterns
        for pattern in self.CDN_PATTERNS:
            if pattern in url_lower:
                return True, 'cdn_url'

        # Check for forum index pages (not individual threads)
        if 'forumdisplay.php' in path:
            return True, 'forum_index'

        # Check for content type pages (not articles)
        if '/content/type/' in path:
            return True, 'content_type_page'

        # Homepage only (no path)
        if path in ['', '/'] and not parsed.query:
            return True, 'homepage_only'

        return False, ''

    def filter_urls(self) -> List[Dict]:
        """Filter all URLs and return clean list."""
        print(f"Starting with {len(self.urls_data)} URLs from Reddit...")

        for url, contexts in self.urls_data.items():
            # Clean URL first
            cleaned_url = self.clean_url(url)

            should_skip, reason = self.should_skip_url(cleaned_url)

            if should_skip:
                self.skip_reasons[reason] += 1
                continue

            # Parse domain
            try:
                parsed = urlparse(cleaned_url)
                domain = parsed.netloc.lower().replace('www.', '')
            except:
                continue

            # Calculate metrics
            mentions = len(contexts)
            total_score = sum(
                c.get('post_score', 0) or c.get('comment_score', 0)
                for c in contexts
            )
            avg_score = total_score / mentions if mentions > 0 else 0

            self.filtered_urls.append({
                'url': cleaned_url,  # Use cleaned URL
                'original_url': url,  # Keep original for reference
                'domain': domain,
                'mentions': mentions,
                'total_score': total_score,
                'avg_score': avg_score,
                'contexts': contexts
            })

        print(f"Filtered to {len(self.filtered_urls)} clean URLs")
        return self.filtered_urls

    def get_domain_stats(self) -> Dict:
        """Get statistics by domain."""
        domain_stats = defaultdict(lambda: {
            'url_count': 0,
            'total_mentions': 0,
            'total_score': 0,
            'urls': []
        })

        for url_data in self.filtered_urls:
            domain = url_data['domain']
            domain_stats[domain]['url_count'] += 1
            domain_stats[domain]['total_mentions'] += url_data['mentions']
            domain_stats[domain]['total_score'] += url_data['total_score']
            domain_stats[domain]['urls'].append({
                'url': url_data['url'],
                'mentions': url_data['mentions'],
                'avg_score': url_data['avg_score']
            })

        # Sort URLs within each domain
        for domain in domain_stats:
            domain_stats[domain]['urls'].sort(
                key=lambda x: (x['mentions'], x['avg_score']),
                reverse=True
            )

        return dict(domain_stats)

    def generate_report(self, domain_stats: Dict, output_path: Path):
        """Generate filtering report."""
        report = []
        report.append("=" * 80)
        report.append("URL FILTERING REPORT")
        report.append("Preparing External Website Scraping Queue")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Original URLs: {len(self.urls_data)}")
        report.append(f"Filtered URLs: {len(self.filtered_urls)}")
        report.append(f"Removed: {len(self.urls_data) - len(self.filtered_urls)}")
        report.append(f"Unique domains: {len(domain_stats)}")
        report.append("")

        # Skip reasons
        report.append("URLS REMOVED BY REASON")
        report.append("-" * 80)
        for reason, count in sorted(self.skip_reasons.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {reason}: {count}")
        report.append("")

        # Top domains
        sorted_domains = sorted(
            domain_stats.items(),
            key=lambda x: (x[1]['url_count'], x[1]['total_mentions']),
            reverse=True
        )

        report.append("TOP DOMAINS FOR SCRAPING")
        report.append("=" * 80)
        report.append(f"{'Domain':<40} {'URLs':<8} {'Mentions':<10} {'Score'}")
        report.append("-" * 80)

        for domain, stats in sorted_domains[:30]:  # Top 30
            report.append(
                f"{domain:<40} {stats['url_count']:<8} "
                f"{stats['total_mentions']:<10} {stats['total_score']}"
            )

        report.append("")
        report.append("=" * 80)

        # Detailed breakdown for top 10
        report.append("\nTOP 10 DOMAINS - DETAILED BREAKDOWN")
        report.append("=" * 80)

        for domain, stats in sorted_domains[:10]:
            report.append(f"\n{domain}")
            report.append(f"  Total URLs: {stats['url_count']}")
            report.append(f"  Total mentions: {stats['total_mentions']}")
            report.append(f"  Total Reddit score: {stats['total_score']}")
            report.append(f"  Top URLs:")

            for i, url_info in enumerate(stats['urls'][:5], 1):
                report.append(f"    {i}. {url_info['url'][:70]}...")
                report.append(f"       Mentions: {url_info['mentions']}, Avg score: {url_info['avg_score']:.1f}")

        report.append("")
        report.append("=" * 80)

        # Write report
        report_text = "\n".join(report)
        print("\n" + report_text)

        with open(output_path, 'w') as f:
            f.write(report_text)

        print(f"\nReport saved to: {output_path}")

    def save_filtered_urls(self, output_path: Path, domain_stats: Dict):
        """Save filtered URLs for production scraping."""

        # Sort domains by priority
        sorted_domains = sorted(
            domain_stats.items(),
            key=lambda x: (x[1]['url_count'], x[1]['total_mentions']),
            reverse=True
        )

        output_data = {
            'summary': {
                'total_urls': len(self.filtered_urls),
                'total_domains': len(domain_stats),
                'generated_at': '2025-11-07'
            },
            'domains': []
        }

        for domain, stats in sorted_domains:
            output_data['domains'].append({
                'domain': domain,
                'url_count': stats['url_count'],
                'total_mentions': stats['total_mentions'],
                'total_score': stats['total_score'],
                'urls': stats['urls']  # Sorted by mentions/score
            })

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"Filtered URLs saved to: {output_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    urls_data_path = base_dir / "reports" / "extracted_urls_full.json"
    filtered_output = base_dir / "data" / "filtered_scraping_urls.json"
    report_output = base_dir / "reports" / "url_filtering_report.txt"

    # Create directories
    filtered_output.parent.mkdir(exist_ok=True)
    report_output.parent.mkdir(exist_ok=True)

    if not urls_data_path.exists():
        print(f"Error: URL data not found at {urls_data_path}")
        print("Run extract_urls.py first.")
        sys.exit(1)

    print("=" * 80)
    print("URL FILTERING - Preparing External Website Scraping")
    print("=" * 80)

    # Filter URLs
    url_filter = URLFilter(urls_data_path)
    filtered_urls = url_filter.filter_urls()

    # Get domain statistics
    print("\nCalculating domain statistics...")
    domain_stats = url_filter.get_domain_stats()

    # Generate report
    print("\nGenerating report...")
    url_filter.generate_report(domain_stats, report_output)

    # Save filtered URLs
    print("\nSaving filtered URLs for production scraping...")
    url_filter.save_filtered_urls(filtered_output, domain_stats)

    print(f"\n✓ Filtering complete!")
    print(f"  Clean URLs: {len(filtered_urls)}")
    print(f"  Domains: {len(domain_stats)}")
    print(f"  Output: {filtered_output}")
    print(f"  Report: {report_output}")


if __name__ == "__main__":
    main()
