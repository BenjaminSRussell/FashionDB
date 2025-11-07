#!/usr/bin/env python3
"""
StyleForum Scraper
Specialized scraper for StyleForum.net - the #1 forum found in Reddit links.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import BaseScraper, ScrapedContent


class StyleForumScraper(BaseScraper):
    """Scraper for StyleForum.net threads."""

    def __init__(self):
        super().__init__("styleforum", "https://www.styleforum.net")

    def search(self, query: str, limit: int = 50) -> list[str]:
        """
        Search StyleForum for threads.
        StyleForum uses /search/ endpoint.
        """
        search_url = f"{self.base_url}/search/{limit}/?q={query}&t=post&c[nodes][0]=1&o=date"

        html = self.fetch_page(search_url)
        if not html:
            return []

        soup = self.parse_html(html)

        # Extract thread URLs from search results
        urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/threads/' in href or '/t/' in href:
                full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                if full_url not in urls:
                    urls.append(full_url)

        return urls[:limit]

    def scrape_content(self, url: str) -> ScrapedContent | None:
        """
        Scrape a StyleForum thread.
        """
        print(f"    Scraping StyleForum: {url}")

        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Extract thread title
        title_elem = soup.find('h1', class_='p-title-value') or soup.find('h1')
        title = self.extract_text(title_elem, "Untitled Thread")

        # Find the first post (original post)
        # StyleForum uses article tags with class 'message'
        posts = soup.find_all('article', class_='message')

        if not posts:
            print(f"    [!] No posts found in thread")
            return None

        first_post = posts[0]

        # Extract author
        author_elem = first_post.find('a', class_='username')
        author = self.extract_text(author_elem)

        # Extract post date
        time_elem = first_post.find('time')
        date = time_elem['datetime'] if time_elem and 'datetime' in time_elem.attrs else None

        # Extract post body
        body_elem = first_post.find('div', class_='bbWrapper') or first_post.find('div', class_='message-body')
        body = self.extract_text(body_elem, "")

        if not body:
            print(f"    [!] No body content found")
            return None

        # Extract replies (up to 50)
        comments = []
        for post in posts[1:51]:  # Skip first post, get next 50
            comment_body_elem = post.find('div', class_='bbWrapper') or post.find('div', class_='message-body')
            comment_author_elem = post.find('a', class_='username')

            if comment_body_elem:
                comment_text = self.extract_text(comment_body_elem)
                comment_author = self.extract_text(comment_author_elem, "Unknown")

                if comment_text:
                    comments.append({
                        'body': self.clean_text(comment_text),
                        'author': comment_author,
                        'score': 0  # StyleForum doesn't have visible scores
                    })

        # Extract tags/categories
        tags = []
        tag_elems = soup.find_all('a', class_='tagItem')
        for tag_elem in tag_elems:
            tag = self.extract_text(tag_elem)
            if tag:
                tags.append(tag)

        print(f"    ✓ Extracted: {len(body)} chars, {len(comments)} replies")

        return ScrapedContent(
            content_id=self.generate_content_id(url),
            source="styleforum.net",
            source_type="forum",
            title=self.clean_text(title),
            url=url,
            body=self.clean_text(body),
            author=author,
            published_date=date,
            comments=comments,
            tags=tags
        )


def main():
    """Test the scraper."""
    scraper = StyleForumScraper()

    # Test URLs from our analysis
    test_urls = [
        "https://www.styleforum.net/threads/the-contentedness-thread.303455/",
        "https://www.styleforum.net/threads/official-sales-alert-thread.38417/page-1030"
    ]

    print("Testing StyleForum Scraper\n")

    for url in test_urls:
        print(f"\nTest URL: {url}")
        content = scraper.scrape_content(url)

        if content:
            print(f"✓ Success!")
            print(f"  Title: {content.title}")
            print(f"  Author: {content.author}")
            print(f"  Body: {len(content.body)} chars")
            print(f"  Comments: {len(content.comments)}")
            print(f"  Tags: {', '.join(content.tags)}")
            print(f"\n  First 200 chars:")
            print(f"  {content.body[:200]}...")
        else:
            print(f"✗ Failed")


if __name__ == "__main__":
    main()
