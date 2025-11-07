#!/usr/bin/env python3
"""
Scrape Web-Search-Discovered URLs - Independent Sources Scraper
Scrapes fashion advice articles discovered via web search (no Reddit bias).
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import ScrapedContent
from scrapers.production_scraper import EnhancedBlogScraper


class WebSearchScraper:
    """Scraper for web-search-discovered fashion advice URLs."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()

        self.stats = {
            'total_attempted': 0,
            'total_success': 0,
            'total_failed': 0,
            'by_topic': {}
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

    def scrape_url(self, url: str, topic: str) -> bool:
        """
        Scrape a single URL.
        Returns True if successful, False otherwise.
        """
        self.stats['total_attempted'] += 1

        if topic not in self.stats['by_topic']:
            self.stats['by_topic'][topic] = {
                'attempted': 0,
                'success': 0,
                'failed': 0
            }

        self.stats['by_topic'][topic]['attempted'] += 1

        # Extract domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
        except:
            domain = 'unknown'

        try:
            # Use generic blog scraper
            scraper = EnhancedBlogScraper(domain, {'delay': 1.0})
            content = scraper.scrape_content(url)

            if content and len(content.body) > 300:
                self.save_content(content)
                self.log_attempt(url, domain, True)
                self.stats['total_success'] += 1
                self.stats['by_topic'][topic]['success'] += 1
                print(f"    ✓ {content.title[:60]}... ({len(content.body)} chars)")
                return True
            else:
                self.log_attempt(url, domain, False, "Insufficient content")
                self.stats['total_failed'] += 1
                self.stats['by_topic'][topic]['failed'] += 1
                print(f"    ✗ Insufficient content")
                return False

        except Exception as e:
            self.log_attempt(url, domain, False, str(e))
            self.stats['total_failed'] += 1
            self.stats['by_topic'][topic]['failed'] += 1
            print(f"    ✗ Error: {str(e)[:50]}")
            return False

    def scrape_all(self, urls_path: Path):
        """Scrape all web-search-discovered URLs."""

        # Load URLs
        with open(urls_path, 'r') as f:
            url_data = json.load(f)

        total_urls = url_data['summary']['total_urls']
        print(f"Loaded {total_urls} URLs from {len(url_data['topics'])} topics\n")

        # Scrape each topic
        for i, topic_data in enumerate(url_data['topics'], 1):
            topic = topic_data['topic']
            urls = topic_data['urls']

            print(f"\n{'='*70}")
            print(f"[{i}/{len(url_data['topics'])}] {topic}")
            print(f"URLs: {len(urls)}")
            print(f"{'='*70}")

            for j, url in enumerate(urls, 1):
                print(f"\n[{j}/{len(urls)}] {url[:60]}...")
                self.scrape_url(url, topic)

                # Respectful delay
                time.sleep(1.5)

            # Brief delay between topics
            time.sleep(2.0)

    def generate_report(self, output_path: Path):
        """Generate scraping report."""

        report = []
        report.append("=" * 80)
        report.append("WEB SEARCH SCRAPING REPORT")
        report.append("Independent Fashion Advice Articles (No Reddit Bias)")
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

        # By topic
        report.append("BY TOPIC")
        report.append("=" * 80)
        report.append(f"{'Topic':<45} {'Success':<10} {'Failed':<10} {'Rate'}")
        report.append("-" * 80)

        for topic, stats in self.stats['by_topic'].items():
            rate = (stats['success'] / stats['attempted'] * 100) if stats['attempted'] > 0 else 0
            report.append(
                f"{topic[:45]:<45} {stats['success']:<10} {stats['failed']:<10} {rate:.1f}%"
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

        cursor.execute("SELECT source, COUNT(*) as count FROM scraped_content GROUP BY source ORDER BY count DESC LIMIT 10")
        by_source = cursor.fetchall()

        conn.close()

        report.append("\nDATABASE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total articles in database: {total_content}")
        report.append(f"Average article length: {int(avg_length):,} characters")
        report.append("")

        report.append("Top 10 sources:")
        for source, count in by_source:
            report.append(f"  {source}: {count}")

        report.append("")
        report.append("=" * 80)
        report.append("\nCONCLUSION")
        report.append("-" * 80)
        report.append(f"✓ Scraped {self.stats['total_success']} independent fashion advice articles")
        report.append(f"✓ No Reddit bias - discovered via web search")
        report.append(f"✓ Diverse topics covered: fashion guides, suits, wardrobe, shoes, colors")
        report.append(f"✓ Average {int(avg_length):,} characters per article")
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

    # Check for command-line argument
    if len(sys.argv) > 1 and sys.argv[1] == '--input':
        urls_path = Path(sys.argv[2])
    else:
        urls_path = base_dir / "data" / "web_search_discovered_urls.json"

    db_path = base_dir / "data" / "independent_content.db"
    report_path = base_dir / "reports" / "web_search_scraping_report.txt"

    # Create directories
    db_path.parent.mkdir(exist_ok=True)
    report_path.parent.mkdir(exist_ok=True)

    if not urls_path.exists():
        print(f"Error: URLs file not found at {urls_path}")
        sys.exit(1)

    print("=" * 80)
    print("WEB SEARCH SCRAPING - Independent Fashion Advice URLs")
    print("=" * 80)
    print(f"Input: {urls_path}")
    print(f"Database: {db_path}")
    print("=" * 80)

    # Initialize scraper
    scraper = WebSearchScraper(db_path)

    # Scrape all URLs
    scraper.scrape_all(urls_path)

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
