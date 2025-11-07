#!/usr/bin/env python3
"""
Discover Article URLs - Find All Articles from Curated Sites
Scrapes category pages to discover all article URLs from curated fashion advice sites.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.production_scraper import EnhancedBlogScraper


class URLDiscoverer:
    """Discovers article URLs from category pages on curated sites."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.discovered_urls = defaultdict(set)
        self.stats = defaultdict(dict)

    def load_sites(self) -> List[Dict]:
        """Load curated site configurations."""
        with open(self.config_path, 'r') as f:
            sites = json.load(f)
        return [s for s in sites if s.get('active', True)]

    def discover_from_site(self, site_config: Dict, max_pages: int = 10) -> Set[str]:
        """
        Discover all article URLs from a site's category pages.

        Args:
            site_config: Site configuration dict
            max_pages: Maximum pagination pages to follow

        Returns:
            Set of discovered article URLs
        """
        domain = site_config['domain']
        name = site_config['name']
        delay = site_config.get('delay', 1.0)

        print(f"\n{'='*70}")
        print(f"Discovering URLs: {name}")
        print(f"Domain: {domain}")
        print(f"{'='*70}")

        discovered = set()
        scraper = EnhancedBlogScraper(domain, site_config)

        # Process each category URL
        for category_url in site_config['urls']:
            print(f"\nCategory: {category_url}")

            # Discover from base category page
            category_discovered = set()

            # Try base page
            try:
                urls = scraper.scrape_category_page(category_url, max_posts=100)
                category_discovered.update(urls)
                print(f"  Page 1: Found {len(urls)} article URLs")
            except Exception as e:
                print(f"  ✗ Error on page 1: {e}")

            time.sleep(delay)

            # Try pagination
            for page_num in range(2, max_pages + 1):
                # Try common pagination patterns
                pagination_patterns = [
                    f"{category_url}/page/{page_num}/",  # WordPress: /category/name/page/2/
                    f"{category_url}page/{page_num}/",   # WordPress alt: /category/name/page/2/
                    f"{category_url}?page={page_num}",   # Query string: /category?page=2
                    f"{category_url}&page={page_num}",   # Query alt: /category?foo=bar&page=2
                ]

                found_on_page = False
                for pagination_url in pagination_patterns:
                    try:
                        urls = scraper.scrape_category_page(pagination_url, max_posts=100)

                        if urls and len(urls) > 0:
                            # Check if these are new URLs (not duplicates from page 1)
                            new_urls = set(urls) - category_discovered
                            if new_urls:
                                category_discovered.update(new_urls)
                                print(f"  Page {page_num}: Found {len(new_urls)} new article URLs")
                                found_on_page = True
                                break  # Found working pagination pattern
                    except Exception as e:
                        continue  # Try next pattern

                if not found_on_page:
                    # No more pages or pagination not working
                    break

                time.sleep(delay)

            discovered.update(category_discovered)
            print(f"  Total from this category: {len(category_discovered)} URLs")

        # Store stats
        self.stats[domain] = {
            'name': name,
            'total_urls': len(discovered),
            'categories_checked': len(site_config['urls'])
        }

        print(f"\n✓ Total URLs discovered for {name}: {len(discovered)}")
        self.discovered_urls[domain] = discovered

        return discovered

    def discover_all(self, sites: List[Dict], max_pages_per_category: int = 10) -> Dict[str, Set[str]]:
        """
        Discover URLs from all sites.

        Args:
            sites: List of site configurations
            max_pages_per_category: Maximum pagination pages to follow per category

        Returns:
            Dict mapping domain to set of discovered URLs
        """
        print(f"Starting URL discovery for {len(sites)} sites...")
        print(f"Max pagination pages per category: {max_pages_per_category}\n")

        for i, site in enumerate(sites, 1):
            print(f"\n[{i}/{len(sites)}] Processing {site['name']}...")

            try:
                self.discover_from_site(site, max_pages=max_pages_per_category)
            except Exception as e:
                print(f"  ✗ Error discovering from {site['domain']}: {e}")
                self.stats[site['domain']] = {
                    'name': site['name'],
                    'total_urls': 0,
                    'error': str(e)
                }

            # Brief delay between sites
            time.sleep(1.5)

        return dict(self.discovered_urls)

    def save_discovered_urls(self, output_path: Path):
        """Save discovered URLs to JSON file."""

        output_data = {
            'summary': {
                'total_sites': len(self.discovered_urls),
                'total_urls': sum(len(urls) for urls in self.discovered_urls.values()),
                'generated_at': '2025-11-07'
            },
            'sites': []
        }

        # Sort by number of URLs discovered
        sorted_sites = sorted(
            self.stats.items(),
            key=lambda x: x[1].get('total_urls', 0),
            reverse=True
        )

        for domain, stats in sorted_sites:
            output_data['sites'].append({
                'domain': domain,
                'name': stats['name'],
                'total_urls': stats.get('total_urls', 0),
                'urls': sorted(list(self.discovered_urls.get(domain, [])))  # Convert set to sorted list
            })

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n✓ Discovered URLs saved to: {output_path}")

    def generate_report(self, output_path: Path):
        """Generate discovery report."""

        report = []
        report.append("=" * 80)
        report.append("URL DISCOVERY REPORT")
        report.append("Article URLs Discovered from Curated Fashion Advice Sites")
        report.append("=" * 80)
        report.append("")

        # Summary
        total_sites = len(self.stats)
        total_urls = sum(len(urls) for urls in self.discovered_urls.values())
        successful_sites = sum(1 for s in self.stats.values() if s.get('total_urls', 0) > 0)

        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Sites checked: {total_sites}")
        report.append(f"Successful discoveries: {successful_sites}")
        report.append(f"Total article URLs discovered: {total_urls}")
        report.append(f"Average URLs per site: {total_urls // successful_sites if successful_sites > 0 else 0}")
        report.append("")

        # Sites by URLs discovered
        sorted_sites = sorted(
            self.stats.items(),
            key=lambda x: x[1].get('total_urls', 0),
            reverse=True
        )

        report.append("SITES BY URLS DISCOVERED")
        report.append("=" * 80)
        report.append(f"{'Name':<45} {'URLs':<10} {'Categories'}")
        report.append("-" * 80)

        for domain, stats in sorted_sites:
            if stats.get('total_urls', 0) > 0:
                report.append(
                    f"{stats['name']:<45} {stats['total_urls']:<10} "
                    f"{stats.get('categories_checked', 0)}"
                )

        report.append("")

        # Failed sites
        failed = [(d, s) for d, s in self.stats.items() if s.get('total_urls', 0) == 0]
        if failed:
            report.append("\nFAILED DISCOVERIES (No URLs Found)")
            report.append("=" * 80)
            for domain, stats in failed:
                error = stats.get('error', 'No URLs discovered')
                report.append(f"{stats['name']}: {error}")

        report.append("")
        report.append("=" * 80)

        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 80)

        if successful_sites >= total_sites * 0.7:
            report.append("✓ Excellent discovery rate - ready for production scraping")
        elif successful_sites >= total_sites * 0.5:
            report.append("⚠ Moderate discovery rate - review failed sites")
        else:
            report.append("✗ Low discovery rate - check site configurations")

        report.append(f"\n{total_urls} article URLs ready to scrape!")
        report.append("")
        report.append("=" * 80)

        # Write report
        report_text = "\n".join(report)
        print("\n" + report_text)

        with open(output_path, 'w') as f:
            f.write(report_text)

        print(f"\nReport saved to: {output_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    config_path = base_dir / "scrapers" / "curated_sites_expanded.json"
    discovered_output = base_dir / "data" / "discovered_article_urls.json"
    report_output = base_dir / "reports" / "url_discovery_report.txt"

    # Create directories
    discovered_output.parent.mkdir(exist_ok=True)
    report_output.parent.mkdir(exist_ok=True)

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    print("=" * 80)
    print("URL DISCOVERY - Finding Article URLs from Curated Sites")
    print("=" * 80)
    print(f"Config: {config_path}")
    print(f"Output: {discovered_output}")
    print("=" * 80)

    # Initialize discoverer
    discoverer = URLDiscoverer(config_path)

    # Load sites
    sites = discoverer.load_sites()
    print(f"\nLoaded {len(sites)} active sites")

    # Discover URLs
    discovered_urls = discoverer.discover_all(sites, max_pages_per_category=10)

    # Save results
    print("\nSaving discovered URLs...")
    discoverer.save_discovered_urls(discovered_output)

    # Generate report
    print("\nGenerating report...")
    discoverer.generate_report(report_output)

    # Summary
    total_urls = sum(len(urls) for urls in discovered_urls.values())
    print(f"\n✓ Discovery complete!")
    print(f"  Sites: {len(discovered_urls)}")
    print(f"  Total article URLs: {total_urls}")
    print(f"  Output: {discovered_output}")
    print(f"  Report: {report_output}")


if __name__ == "__main__":
    main()
