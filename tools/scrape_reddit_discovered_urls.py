#!/usr/bin/env python3
"""
Scrape Reddit-Discovered URLs - Production Scraper
Scrapes external fashion advice articles discovered from Reddit URLs.
Focuses on proven working domains like PutThisOn, StyleForum, etc.
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.putthison_scraper import PutThisOnScraper
from scrapers.styleforum_scraper import StyleForumScraper
from scrapers.base_scraper import ScrapedContent
from scrapers.production_scraper import EnhancedBlogScraper


class ProductionScraper:
    """Production scraper for Reddit-discovered fashion advice URLs."""

    # Focus on fashion ADVICE domains, not shopping
    ADVICE_DOMAINS = {
        'putthison.com',
        'styleforum.net',
        'dappered.com',
        'dieworkwear.com',
        'permanentstyle.com',
        'articlesofstyle.com',
        'streetxsprezza.wordpress.com',
        'nstarleather.wordpress.com',
        'theshoesnobblog.com',
        'medium.com',
        'glenpalmerstyle.com',
        'asuitablewardrobe.com',
        'themodestguy.com',
        'bespokeunit.com',
        'parisiangentleman.com',
        'primermagazine.com',
        'atailoredsuit.com',
        'effortlessgent.com',
        'theperfectgentleman.co.za',
        'kinowear.com',
        'lisbonsuitcompany.com',
        'blacklapel.com',
        'ivystyle.com',
        'sharpography.com',
    }

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.putthison_scraper = PutThisOnScraper()
        self.styleforum_scraper = StyleForumScraper()
        self.init_database()

        self.stats = {
            'total_attempted': 0,
            'total_success': 0,
            'total_failed': 0,
            'by_domain': {}
        }

    def init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_content (
                content_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_type TEXT,
                title TEXT,
                url TEXT UNIQUE,
                body TEXT,
                author TEXT,
                published_date TEXT,
                score INTEGER DEFAULT 0,
                scraped_at TIMESTAMP,
                metadata TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                url TEXT,
                success BOOLEAN,
                error_message TEXT,
                scraped_at TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def get_scraper_for_domain(self, domain: str):
        """Get appropriate scraper for domain."""
        if 'putthison.com' in domain:
            return self.putthison_scraper
        elif 'styleforum.net' in domain:
            return self.styleforum_scraper
        else:
            # Use generic blog scraper
            return EnhancedBlogScraper(domain, {'delay': 1.0})

    def save_content(self, content: ScrapedContent):
        """Save scraped content to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO scraped_content
                (content_id, source, source_type, title, url, body, author,
                 published_date, score, scraped_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content.content_id,
                content.source,
                content.source_type,
                content.title,
                content.url,
                content.body,
                content.author,
                content.published_date,
                content.score,
                content.scraped_at,
                json.dumps(content.metadata)
            ))
            conn.commit()
        finally:
            conn.close()

    def log_attempt(self, url: str, domain: str, success: bool, error: Optional[str] = None):
        """Log scraping attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO scraping_log (source, url, success, error_message, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (domain, url, success, error, datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

    def scrape_url(self, url: str, domain: str) -> bool:
        """
        Scrape a single URL.
        Returns True if successful, False otherwise.
        """
        self.stats['total_attempted'] += 1

        if domain not in self.stats['by_domain']:
            self.stats['by_domain'][domain] = {
                'attempted': 0,
                'success': 0,
                'failed': 0
            }

        self.stats['by_domain'][domain]['attempted'] += 1

        try:
            scraper = self.get_scraper_for_domain(domain)
            content = scraper.scrape_content(url)

            if content and len(content.body) > 300:
                self.save_content(content)
                self.log_attempt(url, domain, True)
                self.stats['total_success'] += 1
                self.stats['by_domain'][domain]['success'] += 1
                print(f"    ✓ {content.title[:60]}... ({len(content.body)} chars)")
                return True
            else:
                self.log_attempt(url, domain, False, "Insufficient content")
                self.stats['total_failed'] += 1
                self.stats['by_domain'][domain]['failed'] += 1
                print(f"    ✗ Insufficient content")
                return False

        except Exception as e:
            self.log_attempt(url, domain, False, str(e))
            self.stats['total_failed'] += 1
            self.stats['by_domain'][domain]['failed'] += 1
            print(f"    ✗ Error: {str(e)[:50]}")
            return False

    def scrape_domain(self, domain: str, urls: List[Dict], delay: float = 1.5):
        """Scrape all URLs for a given domain."""
        print(f"\n{'='*70}")
        print(f"Scraping: {domain}")
        print(f"URLs to scrape: {len(urls)}")
        print(f"{'='*70}")

        for i, url_data in enumerate(urls, 1):
            url = url_data['url']
            print(f"\n[{i}/{len(urls)}] {url[:60]}...")

            self.scrape_url(url, domain)

            # Respectful delay
            time.sleep(delay)

    def scrape_all(self, filtered_urls_path: Path):
        """Scrape all Reddit-discovered URLs from fashion advice domains."""

        # Load filtered URLs
        with open(filtered_urls_path, 'r') as f:
            url_data = json.load(f)

        # Filter to advice domains only
        advice_sites = []
        for site in url_data['domains']:
            domain = site['domain']
            if domain in self.ADVICE_DOMAINS:
                advice_sites.append(site)

        print(f"Found {len(advice_sites)} fashion advice domains")
        print(f"Total URLs to scrape: {sum(s['url_count'] for s in advice_sites)}\n")

        # Sort by priority (more URLs = higher priority)
        advice_sites.sort(key=lambda x: x['url_count'], reverse=True)

        # Scrape each domain
        for i, site in enumerate(advice_sites, 1):
            domain = site['domain']
            urls = site['urls']

            print(f"\n[{i}/{len(advice_sites)}] Processing {domain}...")

            self.scrape_domain(domain, urls)

            # Brief delay between domains
            time.sleep(2.0)

    def generate_report(self, output_path: Path):
        """Generate scraping report."""

        report = []
        report.append("=" * 80)
        report.append("PRODUCTION SCRAPING REPORT")
        report.append("Reddit-Discovered Fashion Advice Articles")
        report.append("=" * 80)
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Total URLs attempted: {self.stats['total_attempted']}")
        report.append(f"Successful scrapes: {self.stats['total_success']}")
        report.append(f"Failed scrapes: {self.stats['total_failed']}")
        success_rate = (self.stats['total_success'] / self.stats['total_attempted'] * 100) if self.stats['total_attempted'] > 0 else 0
        report.append(f"Success rate: {success_rate:.1f}%")
        report.append("")

        # By domain
        sorted_domains = sorted(
            self.stats['by_domain'].items(),
            key=lambda x: x[1]['success'],
            reverse=True
        )

        report.append("BY DOMAIN")
        report.append("=" * 80)
        report.append(f"{'Domain':<40} {'Success':<10} {'Failed':<10} {'Rate'}")
        report.append("-" * 80)

        for domain, stats in sorted_domains:
            rate = (stats['success'] / stats['attempted'] * 100) if stats['attempted'] > 0 else 0
            report.append(
                f"{domain:<40} {stats['success']:<10} {stats['failed']:<10} {rate:.1f}%"
            )

        report.append("")
        report.append("=" * 80)

        # Database stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM scraped_content")
        total_content = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(LENGTH(body)) FROM scraped_content")
        avg_length = cursor.fetchone()[0] or 0

        cursor.execute("SELECT source, COUNT(*) as count FROM scraped_content GROUP BY source ORDER BY count DESC")
        by_source = cursor.fetchall()

        conn.close()

        report.append("\nDATABASE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total articles in database: {total_content}")
        report.append(f"Average article length: {int(avg_length):,} characters")
        report.append("")

        report.append("Articles by source:")
        for source, count in by_source:
            report.append(f"  {source}: {count}")

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

    filtered_urls_path = base_dir / "data" / "filtered_scraping_urls.json"
    db_path = base_dir / "data" / "external_content.db"
    report_path = base_dir / "reports" / "production_scraping_report.txt"

    # Create directories
    db_path.parent.mkdir(exist_ok=True)
    report_path.parent.mkdir(exist_ok=True)

    if not filtered_urls_path.exists():
        print(f"Error: Filtered URLs not found at {filtered_urls_path}")
        print("Run filter_scraping_urls.py first.")
        sys.exit(1)

    print("=" * 80)
    print("PRODUCTION SCRAPING - Reddit-Discovered Fashion Advice URLs")
    print("=" * 80)
    print(f"Input: {filtered_urls_path}")
    print(f"Database: {db_path}")
    print("=" * 80)

    # Initialize scraper
    scraper = ProductionScraper(db_path)

    # Scrape all URLs
    scraper.scrape_all(filtered_urls_path)

    # Generate report
    print("\n" + "=" * 80)
    print("Generating report...")
    scraper.generate_report(report_path)

    print(f"\n✓ Scraping complete!")
    print(f"  Articles scraped: {scraper.stats['total_success']}")
    print(f"  Database: {db_path}")
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
