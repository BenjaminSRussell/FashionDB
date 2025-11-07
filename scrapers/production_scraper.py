#!/usr/bin/env python3
"""
Production Web Scraper
Orchestrates scraping across multiple fashion sources with per-site configurations.
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

from scrapers.base_scraper import BaseScraper, ScrapedContent
from scrapers.styleforum_scraper import StyleForumScraper
from scrapers.putthison_scraper import PutThisOnScraper


class EnhancedBlogScraper(BaseScraper):
    """
    Enhanced blog scraper with site-specific configuration support.
    """

    def __init__(self, domain: str, config: Dict):
        super().__init__(f"blog_{domain}", f"https://{domain}")
        self.config = config
        self.rate_limit_delay = config.get('delay', 1.0)

        # Add site-specific headers from config
        headers = self._build_headers()
        self.session.headers.update(headers)

    def _build_headers(self) -> Dict[str, str]:
        """Build headers based on scraping analysis."""
        headers = {}

        analysis = self.config.get('scraping_analysis', '').lower()

        # Cloudflare bypass headers
        if 'accept-language' in analysis:
            headers['Accept-Language'] = 'en-US,en;q=0.9'

        if 'sec-fetch-dest' in analysis:
            headers['Sec-Fetch-Dest'] = 'document'
            headers['Sec-Fetch-Mode'] = 'navigate'
            headers['Sec-Fetch-Site'] = 'none'

        if 'x-requested-with' in analysis:
            headers['X-Requested-With'] = 'XMLHttpRequest'

        # Avoid Python detection
        if 'python-requests' in analysis:
            headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

        return headers

    def search(self, query: str, limit: int = 50) -> List[str]:
        """Search blog for posts."""
        # Not implemented for generic scraper
        return []

    def scrape_category_page(self, url: str, max_posts: int = 50) -> List[str]:
        """
        Scrape a category/archive page to get post URLs.
        """
        print(f"    Discovering posts from: {url}")

        html = self.fetch_page(url)
        if not html:
            return []

        soup = self.parse_html(html)

        # Find article links
        post_urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Skip navigation, images, etc.
            if any(skip in href for skip in ['#', 'javascript:', '.jpg', '.png', 'category', 'tag']):
                continue

            # Must be from the same domain
            if self.base_url.replace('https://', '') in href or href.startswith('/'):
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"

                # Avoid duplicates
                if href not in post_urls and len(post_urls) < max_posts:
                    # Basic heuristic: post URLs usually have dates or post titles
                    if any(indicator in href for indicator in ['/20', '/blog/', '/post/', '/article/']):
                        post_urls.append(href)

        print(f"    Found {len(post_urls)} potential post URLs")
        return post_urls

    def scrape_content(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a blog post."""
        print(f"      Scraping: {url}")

        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Extract title
        title = None
        for selector in [
            ('h1', {'class': 'entry-title'}),
            ('h1', {'class': 'post-title'}),
            ('h1', {'class': 'article-title'}),
            ('h1', {'class': 'single-title'}),
            ('h1', {}),
        ]:
            elem = soup.find(*selector)
            if elem:
                title = self.extract_text(elem)
                if title:
                    break

        if not title:
            title = "Untitled Post"

        # Extract content
        body = None
        for selector in [
            ('section', {'class': 'entry-content'}),
            ('div', {'class': 'entry-content'}),
            ('div', {'class': 'post-content'}),
            ('div', {'class': 'article-content'}),
            ('article', {'class': 'post'}),
            ('article', {}),
            ('div', {'id': 'content'}),
        ]:
            elem = soup.find(*selector)
            if elem:
                # Remove scripts, styles, ads
                for unwanted in elem(['script', 'style', 'iframe', 'aside', 'nav']):
                    unwanted.decompose()

                body = self.extract_text(elem)
                if len(body) > 300:  # Must have substantial content
                    break

        if not body:
            print(f"        [!] No content found")
            return None

        # Extract author
        author = None
        for selector in [
            ('span', {'class': 'author'}),
            ('a', {'rel': 'author'}),
            ('span', {'class': 'by-author'}),
            ('meta', {'name': 'author'}),
        ]:
            elem = soup.find(*selector)
            if elem:
                if elem.name == 'meta':
                    author = elem.get('content', '')
                else:
                    author = self.extract_text(elem)
                if author:
                    break

        # Extract date
        date = None
        for selector in [
            ('time', {}),
            ('span', {'class': 'published'}),
            ('span', {'class': 'date'}),
            ('meta', {'property': 'article:published_time'}),
        ]:
            elem = soup.find(*selector)
            if elem:
                if elem.name == 'time':
                    date = elem.get('datetime', self.extract_text(elem))
                elif elem.name == 'meta':
                    date = elem.get('content', '')
                else:
                    date = self.extract_text(elem)
                if date:
                    break

        print(f"        ✓ Extracted: {len(body)} chars")

        return ScrapedContent(
            content_id=self.generate_content_id(url),
            source=self.source_name,
            source_type='blog',
            title=self.clean_text(title),
            url=url,
            body=self.clean_text(body),
            author=author,
            published_date=date,
            metadata={'site_config': self.config.get('name', '')}
        )


class ProductionScraper:
    """
    Orchestrates scraping across multiple sources with configuration.
    """

    def __init__(self, config_path: Path, output_db: Path):
        self.config_path = config_path
        self.output_db = output_db
        self.scrapers = {}
        self._init_database()
        self._load_scrapers()

    def _init_database(self):
        """Initialize SQLite database for scraped content."""
        conn = sqlite3.connect(self.output_db)
        cursor = conn.cursor()

        cursor.execute("""
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
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                url TEXT,
                success BOOLEAN,
                error_message TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON scraped_content(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_url ON scraped_content(url)
        """)

        conn.commit()
        conn.close()

    def _load_scrapers(self):
        """Load and initialize scrapers for each configured source."""
        # Built-in scrapers
        self.scrapers['styleforum.net'] = StyleForumScraper()
        self.scrapers['putthison.com'] = PutThisOnScraper()

    def scrape_site(self, site_config: Dict) -> Dict:
        """
        Scrape a single site based on configuration.
        """
        domain = site_config['domain']
        name = site_config['name']

        print(f"\n{'='*70}")
        print(f"SCRAPING: {name} ({domain})")
        print(f"{'='*70}")

        # Check if we have a custom scraper
        if domain in self.scrapers:
            scraper = self.scrapers[domain]
            print(f"Using custom scraper for {domain}")
        else:
            scraper = EnhancedBlogScraper(domain, site_config)
            print(f"Using generic scraper with config")

        results = {
            'site': name,
            'domain': domain,
            'posts_scraped': 0,
            'posts_failed': 0,
            'new_content': 0,
            'duplicate_content': 0
        }

        # Scrape each category URL
        for category_url in site_config['urls']:
            print(f"\nCategory: {category_url}")

            # Get post URLs from category page
            if isinstance(scraper, EnhancedBlogScraper):
                post_urls = scraper.scrape_category_page(category_url, max_posts=50)
            elif domain == 'styleforum.net':
                # For StyleForum, we'd need to implement search or use known URLs
                post_urls = []  # TODO: Implement StyleForum discovery
            else:
                post_urls = []

            # Scrape each post
            for post_url in post_urls[:10]:  # Limit to 10 per category for testing
                content = scraper.scrape_content(post_url)

                if content:
                    saved = self._save_content(content)
                    if saved:
                        results['new_content'] += 1
                    else:
                        results['duplicate_content'] += 1
                    results['posts_scraped'] += 1
                else:
                    results['posts_failed'] += 1

                # Log
                self._log_scrape(domain, post_url, content is not None, None)

        return results

    def _save_content(self, content: ScrapedContent) -> bool:
        """Save scraped content to database. Returns True if new, False if duplicate."""
        conn = sqlite3.connect(self.output_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO scraped_content
                (content_id, source, source_type, title, url, body, author, published_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content.content_id,
                content.source,
                content.source_type,
                content.title,
                content.url,
                content.body,
                content.author,
                content.published_date,
                json.dumps(content.metadata)
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate URL
            return False
        finally:
            conn.close()

    def _log_scrape(self, source: str, url: str, success: bool, error: Optional[str]):
        """Log scraping attempt."""
        conn = sqlite3.connect(self.output_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scraping_log (source, url, success, error_message)
            VALUES (?, ?, ?, ?)
        """, (source, url, success, error))

        conn.commit()
        conn.close()

    def run_production_scrape(self):
        """Run scraping on all configured sites."""
        # Load site configurations
        with open(self.config_path, 'r') as f:
            sites = json.load(f)

        # Filter active sites and sort by priority
        active_sites = [s for s in sites if s.get('active', True)]
        active_sites.sort(key=lambda x: x.get('priority', 0), reverse=True)

        print(f"Starting production scrape of {len(active_sites)} sites")
        print(f"Output database: {self.output_db}\n")

        overall_results = []

        for site in active_sites[:5]:  # Start with top 5 for testing
            results = self.scrape_site(site)
            overall_results.append(results)

            # Report
            print(f"\nResults for {results['site']}:")
            print(f"  Posts scraped: {results['posts_scraped']}")
            print(f"  New content: {results['new_content']}")
            print(f"  Duplicates: {results['duplicate_content']}")
            print(f"  Failed: {results['posts_failed']}")

            # Respect site delay
            delay = site.get('delay', 1.0)
            print(f"\nWaiting {delay}s before next site...")
            time.sleep(delay)

        # Final summary
        print(f"\n{'='*70}")
        print("PRODUCTION SCRAPE COMPLETE")
        print(f"{'='*70}")
        total_scraped = sum(r['posts_scraped'] for r in overall_results)
        total_new = sum(r['new_content'] for r in overall_results)
        total_failed = sum(r['posts_failed'] for r in overall_results)

        print(f"Total posts scraped: {total_scraped}")
        print(f"New content: {total_new}")
        print(f"Failed: {total_failed}")
        print(f"\nData saved to: {self.output_db}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    config_path = base_dir / "scrapers" / "curated_sites.json"
    output_db = base_dir / "data" / "scraped_content.db"

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    # Create data directory
    output_db.parent.mkdir(exist_ok=True)

    # Run scraper
    scraper = ProductionScraper(config_path, output_db)
    scraper.run_production_scrape()


if __name__ == "__main__":
    main()
