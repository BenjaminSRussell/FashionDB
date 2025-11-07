#!/usr/bin/env python3
"""
Base Web Scraper Framework
Foundation for scraping multiple fashion content sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import hashlib
import time
import requests
from bs4 import BeautifulSoup


@dataclass
class ScrapedContent:
    """Standardized content structure from any source."""
    content_id: str
    source: str  # domain
    source_type: str  # 'forum', 'blog', 'article', 'video'
    title: str
    url: str
    body: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    score: int = 0  # likes, upvotes, etc.
    comments: List[Dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'content_id': self.content_id,
            'source': self.source,
            'source_type': self.source_type,
            'title': self.title,
            'url': self.url,
            'body': self.body,
            'author': self.author,
            'published_date': self.published_date,
            'score': self.score,
            'comments': self.comments,
            'tags': self.tags,
            'metadata': self.metadata,
            'scraped_at': self.scraped_at
        }


class BaseScraper(ABC):
    """Base class for all web scrapers."""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; FashionDB/1.0; +https://github.com/fashiondb)'
        })
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0

    def rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def fetch_page(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch a web page with retries and error handling.
        """
        self.rate_limit()

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                print(f"  [!] Fetch failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup."""
        return BeautifulSoup(html, 'html.parser')

    def generate_content_id(self, url: str) -> str:
        """Generate unique content ID from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[str]:
        """
        Search the source for content matching query.
        Returns list of URLs.
        """
        pass

    @abstractmethod
    def scrape_content(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape a single piece of content from URL.
        Returns ScrapedContent or None if failed.
        """
        pass

    def scrape_multiple(self, urls: List[str]) -> List[ScrapedContent]:
        """
        Scrape multiple URLs.
        """
        results = []
        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] Scraping: {url}")
            content = self.scrape_content(url)
            if content:
                results.append(content)
            else:
                print(f"    [!] Failed to scrape")

        return results

    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from BeautifulSoup element."""
        if element is None:
            return default
        return element.get_text(strip=True)

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()


class GenericBlogScraper(BaseScraper):
    """Generic scraper for blogs and article sites."""

    def __init__(self, domain: str, base_url: str):
        super().__init__(f"blog_{domain}", base_url)

    def search(self, query: str, limit: int = 50) -> List[str]:
        """
        Generic blog search - looks for site search or returns empty.
        Override for specific blog implementations.
        """
        print(f"  [!] Generic search not implemented for {self.source_name}")
        return []

    def scrape_content(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape blog post/article content.
        Uses heuristics to find main content.
        """
        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Try to extract title
        title = self.extract_title(soup)

        # Try to extract main content
        body = self.extract_body(soup)

        # Try to extract author and date
        author = self.extract_author(soup)
        date = self.extract_date(soup)

        if not body:
            print(f"    [!] Could not extract body content")
            return None

        return ScrapedContent(
            content_id=self.generate_content_id(url),
            source=self.source_name,
            source_type='blog',
            title=title,
            url=url,
            body=body,
            author=author,
            published_date=date
        )

    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title using common patterns."""
        # Try various selectors
        title_selectors = [
            ('h1', {'class': 'entry-title'}),
            ('h1', {'class': 'post-title'}),
            ('h1', {'class': 'article-title'}),
            ('h1', {}),
            ('title', {})
        ]

        for tag, attrs in title_selectors:
            element = soup.find(tag, attrs)
            if element:
                return self.clean_text(self.extract_text(element))

        return "Untitled"

    def extract_body(self, soup: BeautifulSoup) -> str:
        """Extract article body using common patterns."""
        # Try various content selectors
        content_selectors = [
            ('article', {}),
            ('div', {'class': 'entry-content'}),
            ('div', {'class': 'post-content'}),
            ('div', {'class': 'article-content'}),
            ('div', {'class': 'content'}),
            ('div', {'id': 'content'}),
        ]

        for tag, attrs in content_selectors:
            element = soup.find(tag, attrs)
            if element:
                # Remove script and style elements
                for script in element(['script', 'style']):
                    script.decompose()

                text = self.extract_text(element)
                if len(text) > 200:  # Must have substantial content
                    return self.clean_text(text)

        return ""

    def extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author using common patterns."""
        author_selectors = [
            ('span', {'class': 'author'}),
            ('a', {'rel': 'author'}),
            ('span', {'class': 'by-author'}),
            ('meta', {'name': 'author'})
        ]

        for tag, attrs in author_selectors:
            element = soup.find(tag, attrs)
            if element:
                if tag == 'meta':
                    return element.get('content', '').strip()
                return self.extract_text(element)

        return None

    def extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date."""
        date_selectors = [
            ('time', {}),
            ('span', {'class': 'published'}),
            ('span', {'class': 'date'}),
            ('meta', {'property': 'article:published_time'})
        ]

        for tag, attrs in date_selectors:
            element = soup.find(tag, attrs)
            if element:
                if tag == 'time':
                    return element.get('datetime', self.extract_text(element))
                elif tag == 'meta':
                    return element.get('content', '')
                return self.extract_text(element)

        return None


class GenericForumScraper(BaseScraper):
    """Generic scraper for forum threads."""

    def __init__(self, domain: str, base_url: str):
        super().__init__(f"forum_{domain}", base_url)

    def search(self, query: str, limit: int = 50) -> List[str]:
        """
        Generic forum search.
        Override for specific forum implementations.
        """
        print(f"  [!] Generic search not implemented for {self.source_name}")
        return []

    def scrape_content(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape forum thread.
        Override for specific forum structure.
        """
        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Extract thread title
        title = self.extract_text(soup.find('h1')) or "Untitled Thread"

        # Extract first post (original post)
        posts = soup.find_all('div', class_='post')  # Generic selector
        if not posts:
            return None

        first_post = posts[0]
        body = self.extract_text(first_post)

        # Extract replies
        comments = []
        for post in posts[1:20]:  # Limit to first 20 replies
            comment_text = self.extract_text(post)
            if comment_text:
                comments.append({
                    'body': self.clean_text(comment_text),
                    'score': 0
                })

        return ScrapedContent(
            content_id=self.generate_content_id(url),
            source=self.source_name,
            source_type='forum',
            title=title,
            url=url,
            body=self.clean_text(body),
            comments=comments
        )


def test_scraper(scraper: BaseScraper, test_url: str):
    """Test a scraper on a single URL."""
    print(f"\nTesting {scraper.source_name}...")
    print(f"Test URL: {test_url}")

    content = scraper.scrape_content(test_url)

    if content:
        print("\n✓ Scraping successful!")
        print(f"Title: {content.title}")
        print(f"Body length: {len(content.body)} chars")
        print(f"Author: {content.author}")
        print(f"Date: {content.published_date}")
        print(f"Comments: {len(content.comments)}")
        print("\nFirst 200 chars of body:")
        print(content.body[:200] + "...")
        return True
    else:
        print("\n✗ Scraping failed")
        return False
