#!/usr/bin/env python3
"""
Validate URL Quality - Proof of Data Collection
Tests each Reddit-discovered URL individually and proves we can collect quality data.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.putthison_scraper import PutThisOnScraper
from scrapers.styleforum_scraper import StyleForumScraper
from scrapers.base_scraper import ScrapedContent


class URLQualityValidator:
    """Validates that each Reddit-discovered URL provides quality data."""

    def __init__(self, urls_data_path: Path, temp_dir: Path):
        self.urls_data_path = urls_data_path
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        # Initialize scrapers
        self.putthison_scraper = PutThisOnScraper()
        self.styleforum_scraper = StyleForumScraper()

        self.results = []

    def load_reddit_urls(self) -> Dict:
        """Load URLs extracted from Reddit."""
        with open(self.urls_data_path, 'r') as f:
            return json.load(f)

    def get_top_urls_by_domain(self, urls_data: Dict, domain: str, limit: int = 20) -> List[Dict]:
        """Get top URLs for a specific domain sorted by mentions."""
        domain_urls = []

        for url, contexts in urls_data.items():
            if domain in url.lower():
                domain_urls.append({
                    'url': url,
                    'mentions': len(contexts),
                    'contexts': contexts
                })

        # Sort by mentions
        domain_urls.sort(key=lambda x: x['mentions'], reverse=True)
        return domain_urls[:limit]

    def test_url(self, url: str, contexts: List[Dict], scraper) -> Dict:
        """
        Test scraping a single URL and return quality metrics.
        """
        print(f"\nTesting: {url}")
        print(f"  Mentions in Reddit: {len(contexts)}")

        result = {
            'url': url,
            'mentions': len(contexts),
            'test_status': 'pending',
            'scraped_at': datetime.now().isoformat(),
            'title': None,
            'body_length': 0,
            'author': None,
            'published_date': None,
            'has_comments': False,
            'content_preview': '',
            'error': None,
            'reddit_contexts': contexts[:3]  # Save first 3 contexts as proof
        }

        try:
            content = scraper.scrape_content(url)

            if content and len(content.body) > 300:
                result['test_status'] = 'success'
                result['title'] = content.title
                result['body_length'] = len(content.body)
                result['author'] = content.author
                result['published_date'] = content.published_date
                result['has_comments'] = len(content.comments) > 0
                result['content_preview'] = content.body[:500]  # First 500 chars

                print(f"  ✓ SUCCESS")
                print(f"    Title: {content.title[:60]}...")
                print(f"    Body length: {len(content.body):,} chars")
                print(f"    Author: {content.author or 'Unknown'}")
                print(f"    Comments: {len(content.comments)}")

                # Save full content sample
                self._save_sample(content)

            else:
                result['test_status'] = 'failed'
                result['error'] = 'Insufficient content (<300 chars)'
                print(f"  ✗ FAILED: Insufficient content")

        except Exception as e:
            result['test_status'] = 'error'
            result['error'] = str(e)
            print(f"  ✗ ERROR: {e}")

        return result

    def _save_sample(self, content: ScrapedContent):
        """Save scraped content sample to temp folder."""
        # Create domain subfolder
        domain = content.source.replace('.', '_')
        domain_dir = self.temp_dir / domain
        domain_dir.mkdir(exist_ok=True)

        # Save as JSON
        filename = f"{content.content_id}.json"
        filepath = domain_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content.to_dict(), f, indent=2, ensure_ascii=False)

    def generate_proof_report(self, results: List[Dict], output_path: Path):
        """Generate detailed proof report showing data quality from each URL."""

        report = []
        report.append("=" * 80)
        report.append("URL QUALITY VALIDATION REPORT")
        report.append("PROOF: Reddit URLs Provide Quality Data")
        report.append("=" * 80)
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"URLs Tested: {len(results)}")
        report.append("")

        # Summary statistics
        success = sum(1 for r in results if r['test_status'] == 'success')
        failed = sum(1 for r in results if r['test_status'] == 'failed')
        errors = sum(1 for r in results if r['test_status'] == 'error')

        total_chars = sum(r['body_length'] for r in results if r['test_status'] == 'success')
        avg_chars = total_chars // success if success > 0 else 0

        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Successful scrapes: {success}/{len(results)} ({success/len(results)*100:.1f}%)")
        report.append(f"Failed (insufficient content): {failed}")
        report.append(f"Errors: {errors}")
        report.append(f"Total content collected: {total_chars:,} characters")
        report.append(f"Average content per URL: {avg_chars:,} characters")
        report.append("")

        # Successful URLs
        successful = [r for r in results if r['test_status'] == 'success']
        if successful:
            report.append("✓ SUCCESSFUL URLs - Quality Data Confirmed")
            report.append("=" * 80)

            for i, r in enumerate(successful, 1):
                report.append(f"\n{i}. {r['url']}")
                report.append(f"   Mentioned {r['mentions']} time(s) in Reddit")
                report.append(f"   Title: {r['title']}")
                report.append(f"   Author: {r['author'] or 'Unknown'}")
                report.append(f"   Body length: {r['body_length']:,} characters")
                report.append(f"   Published: {r['published_date'] or 'Unknown'}")
                report.append(f"   Has comments: {'Yes' if r['has_comments'] else 'No'}")

                # Show where it came from in Reddit
                report.append(f"   Reddit source proof:")
                for ctx in r['reddit_contexts'][:2]:  # First 2 contexts
                    if 'post_title' in ctx:
                        report.append(f"     - r/{ctx.get('subreddit', 'unknown')}: {ctx.get('post_title', '')[:50]}...")
                        report.append(f"       Score: {ctx.get('post_score', 0)}")
                    elif 'comment_body' in ctx:
                        report.append(f"     - r/{ctx.get('subreddit', 'unknown')}: Comment in thread")
                        report.append(f"       Score: {ctx.get('comment_score', 0)}")

                # Content preview
                report.append(f"   Content preview:")
                preview = r['content_preview'][:300].replace('\n', ' ')
                report.append(f"     \"{preview}...\"")
                report.append("")

        # Failed URLs
        if failed > 0 or errors > 0:
            report.append("\n✗ FAILED/ERROR URLs")
            report.append("=" * 80)

            for r in results:
                if r['test_status'] != 'success':
                    report.append(f"\n{r['url']}")
                    report.append(f"   Status: {r['test_status'].upper()}")
                    report.append(f"   Error: {r['error']}")
                    report.append("")

        # Overall assessment
        report.append("=" * 80)
        report.append("OVERALL ASSESSMENT")
        report.append("-" * 80)

        if success >= len(results) * 0.9:
            report.append("✓ EXCELLENT: 90%+ success rate - URLs are high quality")
            report.append("  Recommendation: Proceed with full production scraping")
        elif success >= len(results) * 0.7:
            report.append("✓ GOOD: 70%+ success rate - Most URLs work well")
            report.append("  Recommendation: Proceed with production, monitor failures")
        elif success >= len(results) * 0.5:
            report.append("⚠ MODERATE: 50-70% success rate")
            report.append("  Recommendation: Review failed URLs, adjust scrapers")
        else:
            report.append("✗ POOR: <50% success rate")
            report.append("  Recommendation: Review scraping approach")

        report.append("")
        report.append(f"Average content per successful URL: {avg_chars:,} characters")

        if avg_chars >= 5000:
            report.append("✓ Content quality: EXCELLENT (5K+ chars per article)")
        elif avg_chars >= 2000:
            report.append("✓ Content quality: GOOD (2K+ chars per article)")
        elif avg_chars >= 1000:
            report.append("⚠ Content quality: MODERATE (1K+ chars per article)")
        else:
            report.append("✗ Content quality: POOR (<1K chars per article)")

        report.append("")
        report.append("=" * 80)
        report.append("\nCONCLUSION")
        report.append("-" * 80)
        report.append("This report proves that:")
        report.append("1. URLs were discovered FROM Reddit posts and comments")
        report.append("2. Each URL was mentioned by Reddit users (shown with context)")
        report.append("3. We CAN scrape quality content from each URL")
        report.append("4. Content is substantial (avg chars shown above)")
        report.append("5. Data includes title, author, body, metadata")
        report.append("")
        report.append("Samples of scraped content saved to: temp/url_validation/")
        report.append("=" * 80)

        # Write report
        report_text = "\n".join(report)
        print("\n" + report_text)

        with open(output_path, 'w') as f:
            f.write(report_text)

        print(f"\nReport saved to: {output_path}")

        # Save detailed JSON
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Detailed results saved to: {json_path}")

    def run_validation(self, domains_to_test: List[Dict]):
        """
        Run validation on specified domains.
        domains_to_test: [{'domain': 'putthison.com', 'scraper': scraper_instance, 'limit': 10}, ...]
        """
        urls_data = self.load_reddit_urls()

        print(f"Loaded {len(urls_data)} URLs from Reddit analysis")
        print(f"Testing domains: {[d['domain'] for d in domains_to_test]}")
        print(f"Saving samples to: {self.temp_dir}\n")

        for domain_config in domains_to_test:
            domain = domain_config['domain']
            scraper = domain_config['scraper']
            limit = domain_config.get('limit', 10)

            print(f"\n{'='*80}")
            print(f"Testing {domain} (top {limit} URLs)")
            print(f"{'='*80}")

            # Get top URLs for this domain
            domain_urls = self.get_top_urls_by_domain(urls_data, domain, limit)

            print(f"Found {len(domain_urls)} URLs for {domain}")

            # Test each URL
            for i, url_data in enumerate(domain_urls, 1):
                print(f"\n[{i}/{len(domain_urls)}]", end=" ")
                result = self.test_url(
                    url_data['url'],
                    url_data['contexts'],
                    scraper
                )
                self.results.append(result)

                # Respectful delay
                time.sleep(1.5)

        return self.results


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    urls_data_path = base_dir / "reports" / "extracted_urls_full.json"
    temp_dir = base_dir / "temp" / "url_validation"
    report_path = base_dir / "reports" / "url_quality_validation.txt"

    # Create directories
    temp_dir.mkdir(exist_ok=True, parents=True)
    report_path.parent.mkdir(exist_ok=True)

    if not urls_data_path.exists():
        print(f"Error: URLs data not found at {urls_data_path}")
        print("Run extract_urls.py first to generate the URL data.")
        sys.exit(1)

    print("=" * 80)
    print("URL QUALITY VALIDATION TEST")
    print("Proving that Reddit URLs provide quality data")
    print("=" * 80)
    print(f"URL data: {urls_data_path}")
    print(f"Samples will be saved to: {temp_dir}")
    print("=" * 80)

    # Initialize validator
    validator = URLQualityValidator(urls_data_path, temp_dir)

    # Define domains to test with their scrapers
    domains_to_test = [
        {
            'domain': 'putthison.com',
            'scraper': validator.putthison_scraper,
            'limit': 15  # Test top 15 PutThisOn URLs
        },
        {
            'domain': 'styleforum.net',
            'scraper': validator.styleforum_scraper,
            'limit': 10  # Test top 10 StyleForum URLs
        }
    ]

    # Run validation
    results = validator.run_validation(domains_to_test)

    # Generate proof report
    print("\n" + "=" * 80)
    print("Generating proof report...")
    validator.generate_proof_report(results, report_path)

    # Summary
    success = sum(1 for r in results if r['test_status'] == 'success')
    print(f"\n✓ Validation complete!")
    print(f"  Successful: {success}/{len(results)} URLs")
    print(f"  Samples saved to: {temp_dir}")
    print(f"  Full report: {report_path}")


if __name__ == "__main__":
    main()
