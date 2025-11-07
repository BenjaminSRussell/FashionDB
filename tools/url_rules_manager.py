#!/usr/bin/env python3
"""
URL Rules Manager
Loads and applies URL-specific scraping rules from url_scraping_rules.json
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class URLRule:
    """Rule configuration for a specific URL or domain."""
    domain: str
    category: str
    success_rate: float
    tested_urls: int
    successful_urls: int
    requires_browser: bool
    recommended_tool: Optional[str]
    content_selectors: Dict[str, List[str]]
    rate_limit: Dict[str, float]
    notes: str


class URLRulesManager:
    """Manages URL-specific scraping rules and configurations."""

    def __init__(self, rules_file: Optional[Path] = None):
        """Initialize with rules file."""
        if rules_file is None:
            base_dir = Path(__file__).parent.parent
            rules_file = base_dir / "data" / "url_scraping_rules.json"

        self.rules_file = rules_file
        self.rules_data = self._load_rules()

    def _load_rules(self) -> Dict:
        """Load rules from JSON file."""
        with open(self.rules_file, 'r') as f:
            return json.load(f)

    def get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def get_rule_for_url(self, url: str) -> Optional[URLRule]:
        """Get scraping rule for a specific URL."""
        domain = self.get_domain_from_url(url)

        url_rules = self.rules_data.get('url_specific_rules', {})
        if domain not in url_rules:
            return None

        rule_data = url_rules[domain]
        return URLRule(
            domain=domain,
            category=rule_data.get('category', 'unknown'),
            success_rate=rule_data.get('success_rate', 0),
            tested_urls=rule_data.get('tested_urls', 0),
            successful_urls=rule_data.get('successful_urls', 0),
            requires_browser=rule_data.get('requires_browser', False),
            recommended_tool=rule_data.get('recommended_tool'),
            content_selectors=rule_data.get('content_selectors', {}),
            rate_limit=rule_data.get('rate_limit', {}),
            notes=rule_data.get('notes', '')
        )

    def get_category_for_url(self, url: str) -> str:
        """Get category for URL (simple_scraping, javascript_required, etc)."""
        rule = self.get_rule_for_url(url)
        if rule:
            return rule.category
        return 'unknown'

    def requires_chromium(self, url: str) -> bool:
        """Check if URL requires Chromium/browser automation."""
        rule = self.get_rule_for_url(url)
        if rule:
            return rule.requires_browser or rule.category in ['javascript_required', 'cloudflare_protected']
        return False

    def get_recommended_tool(self, url: str) -> str:
        """Get recommended scraping tool for URL."""
        rule = self.get_rule_for_url(url)
        if rule and rule.recommended_tool:
            return rule.recommended_tool

        # Default based on category
        category = self.get_category_for_url(url)
        if category == 'javascript_required':
            return 'playwright or selenium'
        elif category == 'cloudflare_protected':
            return 'undetected-chromedriver or cloudscraper'
        elif category == 'partial_cloudflare':
            return 'requests with retries'
        else:
            return 'requests + beautifulsoup4'

    def get_sites_by_category(self, category: str) -> List[str]:
        """Get all sites in a specific category."""
        categories = self.rules_data.get('site_categories', {})
        if category in categories:
            return categories[category].get('sites', [])
        return []

    def get_all_simple_scraping_sites(self) -> List[str]:
        """Get all sites that work with simple HTTP scraping."""
        return self.get_sites_by_category('simple_scraping')

    def get_all_chromium_sites(self) -> List[str]:
        """Get all sites that require Chromium."""
        js_sites = self.get_sites_by_category('javascript_required')
        cf_sites = self.get_sites_by_category('cloudflare_protected')
        return js_sites + cf_sites

    def should_skip_url(self, url: str, min_success_rate: float = 50.0) -> Tuple[bool, str]:
        """
        Check if URL should be skipped based on success rate.
        Returns (should_skip, reason).
        """
        rule = self.get_rule_for_url(url)

        if not rule:
            return (False, "No rule found - will attempt scraping")

        if rule.success_rate == 0:
            return (True, f"0% success rate - {rule.notes}")

        if rule.success_rate < min_success_rate:
            return (True, f"Low success rate ({rule.success_rate}%) - {rule.notes}")

        return (False, f"Good success rate ({rule.success_rate}%)")

    def get_content_selectors(self, url: str) -> Dict[str, List[str]]:
        """Get content selectors for URL."""
        rule = self.get_rule_for_url(url)
        if rule:
            return rule.content_selectors
        return {}

    def get_rate_limit(self, url: str) -> Dict[str, float]:
        """Get rate limit configuration for URL."""
        rule = self.get_rule_for_url(url)
        if rule:
            return rule.rate_limit

        # Default rate limits
        return {
            'requests_per_minute': 30,
            'delay_between_requests': 2.0
        }

    def print_site_summary(self, url: str):
        """Print summary of site scraping requirements."""
        rule = self.get_rule_for_url(url)

        if not rule:
            print(f"No rule found for {url}")
            return

        print("=" * 80)
        print(f"SCRAPING RULES FOR: {rule.domain}")
        print("=" * 80)
        print(f"Category: {rule.category.upper()}")
        print(f"Success Rate: {rule.success_rate}% ({rule.successful_urls}/{rule.tested_urls} URLs)")
        print()

        if rule.requires_browser:
            print("⚠️  REQUIRES BROWSER AUTOMATION")
            print(f"   Recommended Tool: {rule.recommended_tool}")
            print()

        print(f"Rate Limit:")
        print(f"  - Requests per minute: {rule.rate_limit.get('requests_per_minute', 'N/A')}")
        print(f"  - Delay between requests: {rule.rate_limit.get('delay_between_requests', 'N/A')}s")
        print()

        print(f"Content Selectors:")
        for selector_type, selectors in rule.content_selectors.items():
            print(f"  - {selector_type}: {selectors}")
        print()

        print(f"Notes: {rule.notes}")
        print("=" * 80)

    def export_chromium_sites_list(self, output_file: Path):
        """Export list of sites requiring Chromium to JSON file."""
        chromium_sites = {}

        url_rules = self.rules_data.get('url_specific_rules', {})
        for domain, rule_data in url_rules.items():
            if rule_data.get('requires_browser', False):
                chromium_sites[domain] = {
                    'category': rule_data.get('category'),
                    'recommended_tool': rule_data.get('recommended_tool'),
                    'success_rate': rule_data.get('success_rate'),
                    'notes': rule_data.get('notes')
                }

        with open(output_file, 'w') as f:
            json.dump({
                'chromium_required_sites': chromium_sites,
                'total_sites': len(chromium_sites),
                'tools_needed': list(set(
                    site['recommended_tool']
                    for site in chromium_sites.values()
                    if site.get('recommended_tool')
                ))
            }, f, indent=2)

        print(f"✓ Exported {len(chromium_sites)} Chromium-required sites to {output_file}")

    def generate_scraping_report(self) -> str:
        """Generate comprehensive scraping strategy report."""
        lines = []
        lines.append("=" * 80)
        lines.append("URL SCRAPING RULES SUMMARY")
        lines.append("=" * 80)
        lines.append("")

        # Categories summary
        categories = self.rules_data.get('site_categories', {})
        lines.append("SITE CATEGORIES:")
        lines.append("")
        for cat_name, cat_data in categories.items():
            sites = cat_data.get('sites', [])
            success_rate = cat_data.get('success_rate', 'N/A')
            requirements = cat_data.get('requirements', [])

            lines.append(f"  {cat_name.upper().replace('_', ' ')}")
            lines.append(f"    Sites: {len(sites)}")
            lines.append(f"    Success Rate: {success_rate}")
            lines.append(f"    Requirements: {', '.join(requirements)}")

            if cat_data.get('recommended_tool'):
                lines.append(f"    Recommended Tool: {cat_data['recommended_tool']}")

            lines.append("")

        # URL-specific stats
        url_rules = self.rules_data.get('url_specific_rules', {})
        lines.append(f"TOTAL SITES CONFIGURED: {len(url_rules)}")
        lines.append("")

        # Count by category
        cat_counts = {}
        total_tested = 0
        total_successful = 0

        for domain, rule_data in url_rules.items():
            category = rule_data.get('category', 'unknown')
            cat_counts[category] = cat_counts.get(category, 0) + 1
            total_tested += rule_data.get('tested_urls', 0)
            total_successful += rule_data.get('successful_urls', 0)

        lines.append("SITES BY CATEGORY:")
        for cat, count in sorted(cat_counts.items()):
            lines.append(f"  {cat.replace('_', ' ').title()}: {count} sites")
        lines.append("")

        # Overall stats
        overall_rate = (total_successful / total_tested * 100) if total_tested > 0 else 0
        lines.append(f"OVERALL STATISTICS:")
        lines.append(f"  Total URLs tested: {total_tested}")
        lines.append(f"  Total successful: {total_successful}")
        lines.append(f"  Overall success rate: {overall_rate:.1f}%")
        lines.append("")

        # Top performers
        lines.append("TOP 10 PERFORMING SITES:")
        sorted_sites = sorted(
            url_rules.items(),
            key=lambda x: x[1].get('success_rate', 0),
            reverse=True
        )[:10]

        for domain, rule_data in sorted_sites:
            rate = rule_data.get('success_rate', 0)
            tested = rule_data.get('tested_urls', 0)
            category = rule_data.get('category', 'unknown')
            lines.append(f"  {domain:30s} {rate:5.1f}% ({tested:2d} tested) [{category}]")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """Demo usage of URL rules manager."""
    manager = URLRulesManager()

    # Generate report
    print(manager.generate_scraping_report())
    print()

    # Export Chromium sites
    base_dir = Path(__file__).parent.parent
    output_file = base_dir / "data" / "chromium_required_sites.json"
    manager.export_chromium_sites_list(output_file)
    print()

    # Show examples
    test_urls = [
        "https://putthison.com/finding-the-perfect-loafer/",
        "https://mrporter.com/en-us/journal/fashion/personal-style-25002900",
        "https://thearmoury.com/journal/the-armoury-guide-to-black-tie"
    ]

    for url in test_urls:
        manager.print_site_summary(url)
        print()


if __name__ == "__main__":
    main()
