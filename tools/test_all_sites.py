#!/usr/bin/env python3
"""
Test All Sites - Validation Scraper
Tests scraping on all 25 curated sites and stores results in temp folder.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import ScrapedContent
from scrapers.production_scraper import EnhancedBlogScraper


class SiteValidator:
    """Validates scraping capability for each configured site."""

    def __init__(self, config_path: Path, temp_dir: Path):
        self.config_path = config_path
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.results = []

    def test_site(self, site_config: Dict) -> Dict:
        """
        Test scraping a single site.
        Returns validation results.
        """
        domain = site_config['domain']
        name = site_config['name']

        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"Domain: {domain}")
        print(f"{'='*70}")

        result = {
            'name': name,
            'domain': domain,
            'priority': site_config['priority'],
            'test_status': 'pending',
            'category_pages_tested': 0,
            'category_pages_accessible': 0,
            'post_urls_found': 0,
            'posts_scraped': 0,
            'posts_failed': 0,
            'avg_content_length': 0,
            'errors': [],
            'sample_posts': []
        }

        # Create scraper
        scraper = EnhancedBlogScraper(domain, site_config)

        # Test each category URL
        for category_url in site_config['urls'][:2]:  # Test first 2 categories
            result['category_pages_tested'] += 1

            print(f"\nTesting category: {category_url}")

            try:
                # Try to discover posts
                post_urls = scraper.scrape_category_page(category_url, max_posts=5)

                if post_urls:
                    result['category_pages_accessible'] += 1
                    result['post_urls_found'] += len(post_urls)
                    print(f"  ✓ Found {len(post_urls)} post URLs")

                    # Try to scrape first 2 posts
                    for post_url in post_urls[:2]:
                        try:
                            content = scraper.scrape_content(post_url)

                            if content and len(content.body) > 300:
                                result['posts_scraped'] += 1
                                result['sample_posts'].append({
                                    'url': post_url,
                                    'title': content.title[:60],
                                    'body_length': len(content.body),
                                    'has_author': content.author is not None,
                                    'has_date': content.published_date is not None
                                })
                                print(f"    ✓ Scraped: {content.title[:50]}")
                                print(f"      Length: {len(content.body)} chars")

                                # Save sample to temp folder
                                self._save_sample(domain, content)
                            else:
                                result['posts_failed'] += 1
                                result['errors'].append(f"Insufficient content from {post_url}")
                                print(f"    ✗ Insufficient content")

                        except Exception as e:
                            result['posts_failed'] += 1
                            result['errors'].append(f"Error scraping {post_url}: {str(e)}")
                            print(f"    ✗ Error: {e}")

                        # Brief delay
                        time.sleep(0.5)
                else:
                    result['errors'].append(f"No post URLs found in {category_url}")
                    print(f"  ✗ No post URLs found")

            except Exception as e:
                result['errors'].append(f"Error accessing {category_url}: {str(e)}")
                print(f"  ✗ Error: {e}")

            # Respect delay
            time.sleep(site_config.get('delay', 1.0))

        # Calculate results
        if result['posts_scraped'] > 0:
            result['test_status'] = 'success'
            result['avg_content_length'] = sum(
                p['body_length'] for p in result['sample_posts']
            ) // len(result['sample_posts'])
        elif result['category_pages_accessible'] > 0:
            result['test_status'] = 'partial'
        else:
            result['test_status'] = 'failed'

        return result

    def _save_sample(self, domain: str, content: ScrapedContent):
        """Save a sample scraped post to temp folder."""
        # Create domain subfolder
        domain_dir = self.temp_dir / domain.replace('.', '_')
        domain_dir.mkdir(exist_ok=True)

        # Save as JSON
        filename = f"{content.content_id}.json"
        filepath = domain_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content.to_dict(), f, indent=2, ensure_ascii=False)

    def generate_report(self, results: List[Dict], output_path: Path):
        """Generate comprehensive validation report."""

        report = []
        report.append("=" * 80)
        report.append("SITE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Sites Tested: {len(results)}")
        report.append("")

        # Summary statistics
        success = sum(1 for r in results if r['test_status'] == 'success')
        partial = sum(1 for r in results if r['test_status'] == 'partial')
        failed = sum(1 for r in results if r['test_status'] == 'failed')

        total_scraped = sum(r['posts_scraped'] for r in results)
        total_failed = sum(r['posts_failed'] for r in results)

        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Successful sites: {success} ({success/len(results)*100:.1f}%)")
        report.append(f"Partial success: {partial} ({partial/len(results)*100:.1f}%)")
        report.append(f"Failed sites: {failed} ({failed/len(results)*100:.1f}%)")
        report.append(f"Total posts scraped: {total_scraped}")
        report.append(f"Total posts failed: {total_failed}")
        report.append("")

        # Successful sites
        successful = [r for r in results if r['test_status'] == 'success']
        if successful:
            report.append("SUCCESSFUL SITES (Ready for Production)")
            report.append("-" * 80)
            report.append(f"{'Name':<45} {'Posts':<8} {'Avg Len'}")
            report.append("-" * 80)

            for r in sorted(successful, key=lambda x: x['priority'], reverse=True):
                report.append(
                    f"{r['name']:<45} {r['posts_scraped']:<8} "
                    f"{r['avg_content_length']:>7}ch"
                )
            report.append("")

        # Partial success
        partial_sites = [r for r in results if r['test_status'] == 'partial']
        if partial_sites:
            report.append("PARTIAL SUCCESS (Needs Investigation)")
            report.append("-" * 80)
            report.append(f"{'Name':<45} {'URLs':<8} Issue")
            report.append("-" * 80)

            for r in partial_sites:
                issue = r['errors'][0] if r['errors'] else "Unknown"
                report.append(f"{r['name']:<45} {r['post_urls_found']:<8} {issue[:25]}")
            report.append("")

        # Failed sites
        failed_sites = [r for r in results if r['test_status'] == 'failed']
        if failed_sites:
            report.append("FAILED SITES (Requires Custom Scraper)")
            report.append("-" * 80)
            report.append(f"{'Name':<45} Error")
            report.append("-" * 80)

            for r in failed_sites:
                error = r['errors'][0] if r['errors'] else "Unknown error"
                report.append(f"{r['name']:<45} {error[:30]}")
            report.append("")

        # Detailed results
        report.append("DETAILED RESULTS BY SITE")
        report.append("-" * 80)

        for r in sorted(results, key=lambda x: x['priority'], reverse=True):
            status_symbol = {
                'success': '✓',
                'partial': '⚠',
                'failed': '✗'
            }[r['test_status']]

            report.append(f"\n{status_symbol} {r['name']} ({r['domain']})")
            report.append(f"   Priority: {r['priority']}")
            report.append(f"   Status: {r['test_status'].upper()}")
            report.append(f"   Categories tested: {r['category_pages_tested']}")
            report.append(f"   Categories accessible: {r['category_pages_accessible']}")
            report.append(f"   Post URLs found: {r['post_urls_found']}")
            report.append(f"   Posts scraped: {r['posts_scraped']}")
            report.append(f"   Posts failed: {r['posts_failed']}")

            if r['sample_posts']:
                report.append(f"   Sample posts:")
                for post in r['sample_posts']:
                    report.append(f"     - {post['title']}... ({post['body_length']}ch)")

            if r['errors']:
                report.append(f"   Errors:")
                for error in r['errors'][:3]:  # First 3 errors
                    report.append(f"     - {error}")

        report.append("")
        report.append("=" * 80)

        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 80)

        if success >= len(results) * 0.7:
            report.append("✓ Most sites working well - ready for production scraping")
        elif success >= len(results) * 0.5:
            report.append("⚠ Moderate success - review partial/failed sites before production")
        else:
            report.append("✗ Many sites failing - review scraper configuration")

        if failed_sites:
            report.append(f"\n{len(failed_sites)} sites need custom scrapers:")
            for r in failed_sites[:5]:
                report.append(f"  - {r['domain']}")

        report.append("")
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

    def run_validation(self):
        """Run validation on all sites."""
        # Load site configurations
        with open(self.config_path, 'r') as f:
            sites = json.load(f)

        active_sites = [s for s in sites if s.get('active', True)]

        print(f"Starting validation of {len(active_sites)} sites")
        print(f"Temp folder: {self.temp_dir}")
        print(f"Config: {self.config_path}\n")

        for i, site in enumerate(active_sites, 1):
            print(f"\n[{i}/{len(active_sites)}] Testing {site['name']}...")

            result = self.test_site(site)
            self.results.append(result)

            # Brief pause between sites
            time.sleep(1.0)

        return self.results


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    config_path = base_dir / "scrapers" / "curated_sites.json"
    temp_dir = base_dir / "temp" / "scraping_validation"
    report_path = base_dir / "reports" / "site_validation.txt"

    # Create directories
    temp_dir.mkdir(exist_ok=True, parents=True)
    report_path.parent.mkdir(exist_ok=True)

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    print("=" * 80)
    print("SITE VALIDATION TEST")
    print("=" * 80)
    print(f"This will test scraping on all 25 curated sites")
    print(f"Results will be stored in: {temp_dir}")
    print("=" * 80)

    # Run validation
    validator = SiteValidator(config_path, temp_dir)
    results = validator.run_validation()

    # Generate report
    print("\n" + "=" * 80)
    print("Generating validation report...")
    validator.generate_report(results, report_path)

    # Summary
    success = sum(1 for r in results if r['test_status'] == 'success')
    print(f"\n✓ Validation complete!")
    print(f"  Successful: {success}/{len(results)} sites")
    print(f"  Sample data saved to: {temp_dir}")
    print(f"  Full report: {report_path}")


if __name__ == "__main__":
    main()
