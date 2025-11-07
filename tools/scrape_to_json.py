#!/usr/bin/env python3
"""Scrape URLs and save to JSON - simple, no database."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent))
from scrapers.production_scraper import EnhancedBlogScraper

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "scraped_articles.json"


def load_articles():
    """Load existing articles from JSON."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r') as f:
            return json.load(f)
    return {"articles": [], "metadata": {"total": 0, "last_updated": None}}


def save_articles(data):
    """Save articles to JSON."""
    data["metadata"]["total"] = len(data["articles"])
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def scrape_url(url):
    """Scrape single URL, return article dict or None."""
    domain = urlparse(url).netloc.replace('www.', '')
    scraper = EnhancedBlogScraper(domain, {'delay': 1.0})

    # Try scraping with 3 retries
    for attempt in range(3):
        try:
            content = scraper.scrape_content(url)
            if content and len(content.body) > 300:
                # Create article dict
                return {
                    "id": hashlib.md5(url.encode()).hexdigest(),
                    "url": url,
                    "domain": domain,
                    "title": content.title or "Untitled",
                    "body": content.body,
                    "author": content.author,
                    "date": content.published_date,
                    "word_count": len(content.body.split()),
                    "scraped_at": datetime.now().isoformat()
                }
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            continue
    return None


def scrape_batch(batch_file):
    """Scrape all URLs from batch JSON file."""
    # Load batch
    with open(batch_file, 'r') as f:
        batch = json.load(f)

    # Load existing articles
    data = load_articles()
    existing_urls = {a["url"] for a in data["articles"]}

    # Scrape
    stats = {"attempted": 0, "success": 0, "skipped": 0}

    for topic in batch.get("topics", []):
        print(f"\n[{topic['topic']}]")
        for url in topic["urls"]:
            if url in existing_urls:
                stats["skipped"] += 1
                continue

            stats["attempted"] += 1
            print(f"  {url[:60]}...", end=" ")

            article = scrape_url(url)
            if article:
                data["articles"].append(article)
                stats["success"] += 1
                print(f"✓ {article['word_count']} words")
            else:
                print("✗ failed")

            time.sleep(1)

    # Save
    save_articles(data)

    # Report
    print(f"\nCompleted:")
    print(f"  Attempted: {stats['attempted']}")
    print(f"  Success: {stats['success']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Total articles: {len(data['articles'])}")
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_to_json.py <batch_file.json>")
        sys.exit(1)

    batch_file = Path(sys.argv[1])
    if not batch_file.exists():
        print(f"Error: {batch_file} not found")
        sys.exit(1)

    scrape_batch(batch_file)
