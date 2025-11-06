import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import logging

import requests
from bs4 import BeautifulSoup

# Prefer optional HTTP helpers when available; fall back to requests.
try:
    from curl_cffi import requests as curl_requests

    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    import cloudscraper

    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

try:
    from enhanced_extractor import EnhancedContentExtractor
    from url_utils import normalize_url, is_article_url as url_is_article

    HAS_ENHANCED_EXTRACTOR = True
except ImportError:
    HAS_ENHANCED_EXTRACTOR = False

    def normalize_url(url):
        return url.lower().rstrip("/")


logger = logging.getLogger(__name__)


class ArticleScraper:
    # Scrapes fashion articles while pacing requests and handling basic anti-bot checks.

    def __init__(
        self,
        sites_config_filepath: str = "sites.jsonl",
        output_directory: str = "data/raw",
        request_delay_seconds: float = 1.0,
        min_article_word_count: int = 300,
        min_publication_year: int = 2015,
        request_timeout_seconds: float = 15.0,
        use_enhanced_extractor: bool = True,
    ):
        # Store settings, load sites, and prepare helpers.
        self.sites_config_path = Path(sites_config_filepath)
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.request_delay_seconds = request_delay_seconds
        self.min_article_word_count = min_article_word_count
        self.min_publication_year = min_publication_year
        self.request_timeout_seconds = request_timeout_seconds

        self.site_configs = self._load_sites_configuration()

        self.session = self._initialize_http_session()

        self.use_enhanced = use_enhanced_extractor and HAS_ENHANCED_EXTRACTOR
        self.enhanced_extractor = (
            EnhancedContentExtractor() if self.use_enhanced else None
        )

        self.visited_urls: Set[str] = set()
        self.scraped_articles: List[Dict] = []

        logger.info("Scraper initialized")
        logger.info(f"  Sites loaded: {len(self.site_configs)}")
        logger.info(
            f"  Active sites: {sum(1 for site in self.site_configs if site.get('active'))}"
        )
        logger.info(f"  Enhanced extraction: {self.use_enhanced}")
        logger.info(f"  Cloudflare bypass: {HAS_CURL_CFFI or HAS_CLOUDSCRAPER}")

    def _load_sites_configuration(self) -> List[Dict]:
        # Read active sites from the JSONL config.
        if not self.sites_config_path.exists():
            raise FileNotFoundError(
                f"Sites config not found: {self.sites_config_path}"
            )

        sites = []
        with self.sites_config_path.open("r") as config_file:
            for line in config_file:
                line = line.strip()
                if line:
                    site_config = json.loads(line)
                    if site_config.get("active", True):
                        sites.append(site_config)

        return sites

    def _initialize_http_session(self):
        # Set up an HTTP session with the best available tooling.
        if HAS_CURL_CFFI:
            logger.info("Using curl_cffi for Cloudflare bypass")
            return curl_requests.Session()

        if HAS_CLOUDSCRAPER:
            logger.info("Using cloudscraper for Cloudflare bypass")
            return cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "darwin", "desktop": True}
            )

        logger.warning("No Cloudflare bypass available - using basic requests")
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        return session

    def fetch_html_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        # Fetch HTML with simple retry handling for transient failures.
        for attempt in range(max_retries):
            try:
                time.sleep(self.request_delay_seconds)

                if HAS_CURL_CFFI:
                    response = self.session.get(
                        url,
                        timeout=self.request_timeout_seconds,
                        impersonate="chrome120",
                    )
                else:
                    response = self.session.get(
                        url,
                        timeout=self.request_timeout_seconds,
                        allow_redirects=True,
                    )

                if response.status_code == 403:
                    logger.warning(f"403 Forbidden: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return None

                response.raise_for_status()
                return response.text

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{max_retries}: {url}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue

            except Exception as error:
                logger.error(f"Error fetching {url}: {error}")
                return None

        return None

    def extract_article_hyperlinks(
        self, html_content: str, base_url: str
    ) -> List[str]:
        # Parse likely article links using common selectors.
        soup = BeautifulSoup(html_content, "lxml")
        article_links = []

        link_selectors = [
            "article a[href]",
            ".post-title a[href]",
            ".entry-title a[href]",
            "h2 a[href]",
            "h3 a[href]",
            "main a[href]",
        ]

        seen_links = set()

        for selector in link_selectors:
            for anchor_tag in soup.select(selector):
                href = anchor_tag.get("href")
                if not href:
                    continue

                absolute_url = urljoin(base_url, href)

                normalized_href = normalize_url(absolute_url)

                if not self._is_valid_article_url(normalized_href):
                    continue

                if normalized_href not in seen_links:
                    seen_links.add(normalized_href)
                    article_links.append(normalized_href)

        return article_links

    def _is_valid_article_url(self, url: str) -> bool:
        # Use path heuristics to skip obvious non-article pages.
        url_lower = url.lower()

        blocked_fragments = [
            "/tag/",
            "/tags/",
            "/category/",
            "/categories/",
            "/author/",
            "/search",
            "/page/",
            "/feed/",
            "/rss/",
            "/product/",
            "/shop/",
            "/cart/",
            "/about/",
            "/contact/",
        ]

        if any(fragment in url_lower for fragment in blocked_fragments):
            return False

        parsed_url = urlparse(url)
        path_segments = [p for p in parsed_url.path.split("/") if p]

        return len(path_segments) >= 1

    def scrape_single_article(self, url: str) -> Optional[Dict]:
        # Skip duplicates, fetch HTML, and extract a single article.
        normalized_url = normalize_url(url)
        if normalized_url in self.visited_urls:
            return None

        self.visited_urls.add(normalized_url)

        html_content = self.fetch_html_content(url)
        if not html_content:
            logger.debug(f"Failed to fetch: {url}")
            return None

        try:
            if self.use_enhanced and self.enhanced_extractor:
                article_data = self.enhanced_extractor.extract_article(
                    html_content, url
                )
                article_data["raw_url"] = url
                article_data["normalized_url"] = normalized_url
            else:
                article_data = self._perform_basic_extraction(html_content, url)
                article_data["normalized_url"] = normalized_url

        except Exception as error:
            logger.error(f"Extraction failed for {url}: {error}")
            return None

        if not self._should_keep_scraped_article(article_data):
            return None

        return article_data

    def _perform_basic_extraction(self, html_content: str, url: str) -> Dict:
        # Minimal parser used when the enhanced extractor is unavailable.
        soup = BeautifulSoup(html_content, "lxml")

        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        title_element = soup.find("h1")
        title_text = title_element.get_text(strip=True) if title_element else ""

        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        article_text = " ".join(paragraphs)
        word_count = len(article_text.split())

        return {
            "url": url,
            "title": title_text,
            "author": None,
            "publish_date": None,
            "text": article_text,
            "paragraphs": paragraphs,
            "word_count": word_count,
            "content_type": "general",
        }

    def _should_keep_scraped_article(self, article_data: Dict) -> bool:
        # Filter out entries without a title, too short, or too old.
        if not article_data.get("title"):
            logger.debug("Skipping: no title")
            return False

        article_word_count = article_data.get("word_count", 0)
        if article_word_count < self.min_article_word_count:
            logger.debug(f"Skipping: too short ({article_word_count} words)")
            return False

        if article_data.get("publish_date"):
            try:
                import re

                year_match = re.search(r"(\d{4})", article_data["publish_date"])
                if year_match:
                    year = int(year_match.group(1))
                    if year < self.min_publication_year:
                        logger.debug(f"Skipping: too old ({year})")
                        return False
            except Exception:
                pass

        return True

    def scrape_website(
        self, site_config: Dict, max_articles_to_scrape: int = 100
    ) -> List[Dict]:
        # Scrape one site and return the collected article payloads.
        site_name = site_config.get("name", "Unknown")
        logger.info(f"Scraping site: {site_name}")

        site_articles = []
        candidate_urls = []

        for base_url in site_config.get("urls", []):
            logger.info(f"  Fetching links from: {base_url}")
            html_content = self.fetch_html_content(base_url)
            if html_content:
                article_links = self.extract_article_hyperlinks(
                    html_content, base_url
                )
                candidate_urls.extend(article_links)
                logger.info(f"    Found {len(article_links)} article links")

        candidate_urls = list(set(candidate_urls))
        logger.info(f"  Total unique articles found: {len(candidate_urls)}")

        if len(candidate_urls) > max_articles_to_scrape:
            candidate_urls = candidate_urls[:max_articles_to_scrape]
            logger.info(f"  Limited to {max_articles_to_scrape} articles")

        for url in candidate_urls:
            article_record = self.scrape_single_article(url)
            if article_record:
                article_record["site_name"] = site_name
                article_record["site_domain"] = site_config.get("domain")
                site_articles.append(article_record)

        logger.info(f"  Successfully scraped {len(site_articles)} articles from {site_name}")
        return site_articles

    def scrape_all_websites(self, max_articles_per_site: int = 100) -> List[Dict]:
        # Drive scraping across all configured sites.
        all_articles = []

        for site_config in self.site_configs:
            try:
                articles_from_site = self.scrape_website(
                    site_config, max_articles_per_site
                )
                all_articles.extend(articles_from_site)

                self._save_articles_to_file(
                    articles_from_site, site_config.get("domain", "unknown")
                )

            except Exception as error:
                logger.error(
                    f"Error scraping {site_config.get('name')}: {error}"
                )
                continue

        logger.info(f"\nTotal articles scraped: {len(all_articles)}")
        return all_articles

    def _save_articles_to_file(self, articles: List[Dict], domain: str):
        # Append article JSONL records for a domain.
        if not articles:
            return

        output_filepath = self.output_dir / f"{domain}_articles.jsonl"

        with output_filepath.open("a", encoding="utf-8") as output_file:
            for article in articles:
                output_file.write(json.dumps(article, ensure_ascii=False) + "\n")

        logger.info(f"  Saved {len(articles)} articles to {output_filepath}")


def main():
    # Simple CLI hook for manual runs.
    import argparse

    parser = argparse.ArgumentParser(description="Scrape fashion articles")
    parser.add_argument(
        "--sites", default="sites.jsonl", help="Sites config file"
    )
    parser.add_argument("--output", default="data/raw", help="Output directory")
    parser.add_argument(
        "--max-per-site", type=int, default=50, help="Max articles per site"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests"
    )
    parser.add_argument(
        "--min-words", type=int, default=300, help="Minimum word count"
    )
    parser.add_argument(
        "--min-year", type=int, default=2015, help="Minimum publication year"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    article_scraper = ArticleScraper(
        sites_config_filepath=args.sites,
        output_directory=args.output,
        request_delay_seconds=args.delay,
        min_article_word_count=args.min_words,
        min_publication_year=args.min_year,
    )

    articles = article_scraper.scrape_all_websites(
        max_articles_per_site=args.max_per_site
    )

    print("\nSUCCESS: Scraping complete!")
    print(f"   Total articles: {len(articles)}")
    print(f"   Output: {article_scraper.output_dir}")


if __name__ == "__main__":
    main()
