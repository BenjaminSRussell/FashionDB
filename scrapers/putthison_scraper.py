#!/usr/bin/env python3
"""
PutThisOn Scraper
Specialized scraper for PutThisOn.com - high-quality menswear blog.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import BaseScraper, ScrapedContent


class PutThisOnScraper(BaseScraper):
    """Scraper for PutThisOn.com blog posts."""

    def __init__(self):
        super().__init__("putthison", "https://putthison.com")

    def search(self, query: str, limit: int = 50) -> list[str]:
        """
        Search PutThisOn for posts.
        PutThisOn is a Tumblr blog, so we can use their search.
        """
        # PutThisOn uses WordPress, search endpoint
        search_url = f"{self.base_url}/?s={query}"

        html = self.fetch_page(search_url)
        if not html:
            return []

        soup = self.parse_html(html)

        # Extract post URLs
        urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'putthison.com' in href and '?' not in href:
                if href not in urls:
                    urls.append(href)

        return urls[:limit]

    def scrape_content(self, url: str) -> ScrapedContent | None:
        """
        Scrape a PutThisOn blog post.
        """
        print(f"    Scraping PutThisOn: {url}")

        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Extract title
        # Try multiple selectors
        title = None
        title_selectors = [
            soup.find('h1', class_='entry-title'),
            soup.find('h1', class_='post-title'),
            soup.find('h2', class_='post-title'),
            soup.find('h1'),
        ]

        for elem in title_selectors:
            if elem:
                title = self.extract_text(elem)
                if title:
                    break

        if not title:
            title = "Untitled Post"

        # Extract post content
        body = None
        content_selectors = [
            soup.find('section', class_='entry-content'),
            soup.find('div', class_='entry-content'),
            soup.find('div', class_='post-content'),
            soup.find('article'),
            soup.find('div', id='content'),
        ]

        for elem in content_selectors:
            if elem:
                # Remove script and style tags
                for unwanted in elem(['script', 'style', 'iframe']):
                    unwanted.decompose()

                body = self.extract_text(elem)
                if len(body) > 200:  # Must have substantial content
                    break

        if not body:
            print(f"    [!] No body content found")
            return None

        # Extract author
        author_elem = soup.find('span', class_='author') or soup.find('a', rel='author')
        author = self.extract_text(author_elem, "Put This On")

        # Extract date
        date = None
        date_elem = soup.find('time') or soup.find('span', class_='date')
        if date_elem:
            if date_elem.name == 'time' and 'datetime' in date_elem.attrs:
                date = date_elem['datetime']
            else:
                date = self.extract_text(date_elem)

        # Extract tags
        tags = []
        tag_container = soup.find('div', class_='tags') or soup.find('ul', class_='post-categories')
        if tag_container:
            for tag_elem in tag_container.find_all(['a', 'span']):
                tag = self.extract_text(tag_elem)
                if tag:
                    tags.append(tag)

        print(f"    ✓ Extracted: {len(body)} chars")

        return ScrapedContent(
            content_id=self.generate_content_id(url),
            source="putthison.com",
            source_type="blog",
            title=self.clean_text(title),
            url=url,
            body=self.clean_text(body),
            author=author,
            published_date=date,
            tags=tags
        )


def main():
    """Test the scraper."""
    scraper = PutThisOnScraper()

    # Test URLs from our analysis
    test_urls = [
        "https://putthison.com/five-starting-places-for-building-a-casual-wardrobe/",
        "https://putthison.com/how-to-understand-silhouettes-pt-two/",
    ]

    print("Testing PutThisOn Scraper\n")

    for url in test_urls:
        print(f"\nTest URL: {url}")
        content = scraper.scrape_content(url)

        if content:
            print(f"✓ Success!")
            print(f"  Title: {content.title}")
            print(f"  Author: {content.author}")
            print(f"  Date: {content.published_date}")
            print(f"  Body: {len(content.body)} chars")
            print(f"  Tags: {', '.join(content.tags)}")
            print(f"\n  First 300 chars:")
            print(f"  {content.body[:300]}...")
        else:
            print(f"✗ Failed")


if __name__ == "__main__":
    main()
