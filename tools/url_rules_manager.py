#!/usr/bin/env python3
"""URL rules - check scraping requirements per domain."""

import json
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent.parent
RULES_FILE = BASE_DIR / "data" / "url_scraping_rules.json"


class URLRules:
    """Load and check URL-specific scraping rules."""

    def __init__(self):
        with open(RULES_FILE, 'r') as f:
            self.data = json.load(f)

    def get_domain(self, url):
        """Extract domain from URL."""
        return urlparse(url).netloc.replace('www.', '')

    def get_rule(self, url):
        """Get rule for URL, return None if not found."""
        domain = self.get_domain(url)
        return self.data.get('url_specific_rules', {}).get(domain)

    def requires_chromium(self, url):
        """Check if URL needs browser automation."""
        rule = self.get_rule(url)
        if not rule:
            return False
        return rule.get('requires_browser', False) or \
               rule.get('category') in ['javascript_required', 'cloudflare_protected']

    def get_success_rate(self, url):
        """Get success rate for URL."""
        rule = self.get_rule(url)
        return rule.get('success_rate', 0) if rule else 0

    def print_summary(self, url):
        """Print rule summary for URL."""
        rule = self.get_rule(url)
        if not rule:
            print(f"No rule for {url}")
            return

        domain = self.get_domain(url)
        print(f"\n{domain}")
        print(f"  Category: {rule.get('category')}")
        print(f"  Success: {rule.get('success_rate')}%")
        print(f"  Chromium: {'Yes' if rule.get('requires_browser') else 'No'}")
        if rule.get('recommended_tool'):
            print(f"  Tool: {rule.get('recommended_tool')}")
        print(f"  Notes: {rule.get('notes', '')}")


def main():
    """Show summary."""
    rules = URLRules()

    # Stats
    url_rules = rules.data.get('url_specific_rules', {})
    print(f"Total sites configured: {len(url_rules)}")

    # Top performers
    print("\nTop 10 sites:")
    sorted_sites = sorted(
        url_rules.items(),
        key=lambda x: x[1].get('success_rate', 0),
        reverse=True
    )[:10]

    for domain, rule in sorted_sites:
        rate = rule.get('success_rate', 0)
        tested = rule.get('tested_urls', 0)
        print(f"  {domain:30s} {rate:5.1f}% ({tested} tested)")

    # Chromium sites
    chromium_file = BASE_DIR / "data" / "chromium_required_sites.json"
    with open(chromium_file, 'r') as f:
        chromium_data = json.load(f)

    print(f"\nChromium required: {chromium_data['total_sites']} sites")
    for domain in chromium_data['chromium_required_sites']:
        print(f"  - {domain}")


if __name__ == "__main__":
    main()
