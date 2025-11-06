import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import logging

import requests
from bs4 import BeautifulSoup

# The following try/except blocks are a design choice to gracefully handle optional
# dependencies. We prefer to use more advanced libraries for HTTP requests if they are
# available, as they can help bypass anti-scraping measures like Cloudflare. However,
# by wrapping the imports in a try/except block, we ensure that the scraper can still
# function in a more basic mode even if these libraries are not installed. This
# improves the usability and robustness of the scraper.
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
    # The `ArticleScraper` class is designed to be a robust and flexible tool for
    # collecting a corpus of fashion articles. The core design philosophy is to be
    # respectful of the websites being scraped by including delays between requests,
    # and to be resilient to common scraping challenges like anti-bot measures and
    # inconsistent HTML structures. The use of a configurable list of sites and a
    # modular architecture are deliberate choices to make the scraper easy to extend
    # and maintain.

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
        # The constructor initializes the scraper with its configuration. The parameters
        # are designed to be configurable, allowing for flexibility in different
        # environments and use cases. The initialization of the HTTP session and the
        # content extractor are handled here to ensure that the scraper is in a valid
        # state upon instantiation.
        self.sites_config_filepath = Path(sites_config_filepath)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

        self.request_delay_seconds = request_delay_seconds
        self.min_article_word_count = min_article_word_count
        self.min_publication_year = min_publication_year
        self.request_timeout_seconds = request_timeout_seconds

        self.sites_to_scrape = self._load_sites_configuration()

        self.http_session = self._initialize_http_session()

        self.use_enhanced_extractor = (
            use_enhanced_extractor and HAS_ENHANCED_EXTRACTOR
        )
        self.content_extractor = (
            EnhancedContentExtractor() if self.use_enhanced_extractor else None
        )

        self.visited_urls_set: Set[str] = set()
        self.scraped_articles_list: List[Dict] = []

        logger.info("Scraper initialized")
        logger.info(f"  Sites loaded: {len(self.sites_to_scrape)}")
        logger.info(
            f"  Active sites: {sum(1 for s in self.sites_to_scrape if s.get('active'))}"
        )
        logger.info(f"  Enhanced extraction: {self.use_enhanced_extractor}")
        logger.info(
            f"  Cloudflare bypass: {HAS_CURL_CFFI or HAS_CLOUDSCRAPER}"
        )

    def _load_sites_configuration(self) -> List[Dict]:
        # The use of a separate configuration file for the sites to be scraped is a
        # deliberate design choice to separate configuration from code. This makes it
        # easy to add, remove, or temporarily disable sites without modifying the scraper
        # itself. The JSONL format is chosen for its simplicity and readability.
        if not self.sites_config_filepath.exists():
            raise FileNotFoundError(
                f"Sites config not found: {self.sites_config_filepath}"
            )

        sites = []
        with self.sites_config_filepath.open("r") as config_file:
            for line in config_file:
                line = line.strip()
                if line:
                    site_config = json.loads(line)
                    if site_config.get("active", True):
                        sites.append(site_config)

        return sites

    def _initialize_http_session(self):
        # This method encapsulates the logic for setting up the HTTP session. The
        # progressive enhancement approach (preferring `curl_cffi`, then `cloudscraper`,
        # and finally falling back to `requests`) is a key design choice for maximizing
        # the scraper's ability to bypass anti-bot measures. This makes the scraper
        # more robust and more likely to succeed in a variety of environments.
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
        # This method is responsible for fetching the HTML content of a URL. The inclusion
        # of a retry mechanism with a delay is a deliberate design choice to make the
        # scraper more resilient to transient network errors and temporary server issues.
        # This improves the overall reliability of the scraping process.
        for attempt in range(max_retries):
            try:
                time.sleep(self.request_delay_seconds)

                if HAS_CURL_CFFI:
                    response = self.http_session.get(
                        url,
                        timeout=self.request_timeout_seconds,
                        impersonate="chrome120",
                    )
                else:
                    response = self.http_session.get(
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

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                return None

        return None

    def extract_article_hyperlinks(self, html_content: str, base_url: str) -> List[str]:
        # This method is responsible for finding potential article links on a given page.
        # The use of a list of common CSS selectors is a heuristic-based approach to
        # identify links that are likely to lead to articles. This is a pragmatic choice
        # that works well for many websites, and it can be easily extended to support
        # new site structures.
        soup = BeautifulSoup(html_content, "lxml")
        article_hyperlinks = []

        css_selectors = [
            "article a[href]",
            ".post-title a[href]",
            ".entry-title a[href]",
            "h2 a[href]",
            "h3 a[href]",
            "main a[href]",
        ]

        seen_urls = set()

        for selector in css_selectors:
            for anchor_tag in soup.select(selector):
                href_attribute = anchor_tag.get("href")
                if not href_attribute:
                    continue

                absolute_url = urljoin(base_url, href_attribute)

                normalized_url = normalize_url(absolute_url)

                if not self._is_valid_article_url(normalized_url):
                    continue

                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    article_hyperlinks.append(normalized_url)

        return article_hyperlinks

    def _is_valid_article_url(self, url: str) -> bool:
        # This method is a set of heuristics for determining whether a URL is likely to
        # be an article. The use of a blocklist of common non-article URL patterns is a
        # simple but effective way to filter out a large amount of noise. This is a
        # pragmatic choice that improves the efficiency of the scraper by focusing its
        # efforts on the most promising links.
        url_lower = url.lower()

        excluded_patterns = [
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

        if any(pattern in url_lower for pattern in excluded_patterns):
            return False

        parsed_url = urlparse(url)
        path_segments = [p for p in parsed_url.path.split("/") if p]

        return len(path_segments) >= 1

    def scrape_single_article(self, url: str) -> Optional[Dict]:
        # This method encapsulates the logic for scraping a single article. It is designed
        # to be a self-contained unit of work that can be called from the main scraping
        # loop. The use of the `visited_urls_set` is a crucial design choice to avoid
        # re-scraping the same article, which is essential for efficiency and for
        # preventing duplicate data.
        normalized_url = normalize_url(url)
        if normalized_url in self.visited_urls_set:
            return None

        self.visited_urls_set.add(normalized_url)

        html_content = self.fetch_html_content(url)
        if not html_content:
            logger.debug(f"Failed to fetch: {url}")
            return None

        try:
            if self.use_enhanced_extractor and self.content_extractor:
                article_data = self.content_extractor.extract_article(
                    html_content, url
                )
                article_data["raw_url"] = url
                article_data["normalized_url"] = normalized_url
            else:
                article_data = self._perform_basic_extraction(html_content, url)
                article_data["normalized_url"] = normalized_url

        except Exception as e:
            logger.error(f"Extraction failed for {url}: {e}")
            return None

        if not self._should_keep_scraped_article(article_data):
            return None

        return article_data

    def _perform_basic_extraction(self, html_content: str, url: str) -> Dict:
        # This method provides a fallback mechanism for content extraction. While the
        # `EnhancedContentExtractor` is preferred, this basic extraction ensures that
        # the scraper can still function even if the enhanced extractor is not available.
        # This is a good example of a graceful degradation design pattern.
        soup = BeautifulSoup(html_content, "lxml")

        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        title_element = soup.find("h1")
        title_text = title_element.get_text(strip=True) if title_element else ""

        paragraphs_list = [p.get_text(strip=True) for p in soup.find_all("p")]
        article_text = " ".join(paragraphs_list)

        return {
            "url": url,
            "title": title_text,
            "author": None,
            "publish_date": None,
            "text": article_text,
            "paragraphs": paragraphs_list,
            "word_count": len(article_text.split()),
            "content_type": "general",
        }

    def _should_keep_scraped_article(self, article_data: Dict) -> bool:
        # This method is a set of quality control checks to ensure that we only save
        # high-quality articles. The checks for a title, a minimum word count, and a
        # recent publication date are all designed to filter out low-quality content,
        # such as stubs, teasers, and very old articles. This is a pragmatic choice to
        # improve the quality of our dataset.
        if not article_data.get("title"):
            logger.debug("Skipping: no title")
            return False

        word_count = article_data.get("word_count", 0)
        if word_count < self.min_article_word_count:
            logger.debug(f"Skipping: too short ({word_count} words)")
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
            except:
                pass

        return True

    def scrape_website(self, site_config: Dict, max_articles_to_scrape: int = 100) -> List[Dict]:
        # This method orchestrates the scraping of a single website. It is designed to
        # be a self-contained unit of work that can be called from the main scraping
        # loop. The logging statements are a deliberate choice to provide clear
        # feedback on the progress of the scraping process.
        site_name = site_config.get("name", "Unknown")
        logger.info(f"Scraping site: {site_name}")

        scraped_articles = []
        article_urls_to_scrape = []

        for base_url in site_config.get("urls", []):
            logger.info(f"  Fetching links from: {base_url}")
            html_content = self.fetch_html_content(base_url)
            if html_content:
                hyperlinks = self.extract_article_hyperlinks(html_content, base_url)
                article_urls_to_scrape.extend(hyperlinks)
                logger.info(f"    Found {len(hyperlinks)} article links")

        article_urls_to_scrape = list(set(article_urls_to_scrape))
        logger.info(
            f"  Total unique articles found: {len(article_urls_to_scrape)}"
        )

        if len(article_urls_to_scrape) > max_articles_to_scrape:
            article_urls_to_scrape = article_urls_to_scrape[:max_articles_to_scrape]
            logger.info(f"  Limited to {max_articles_to_scrape} articles")

        for url in article_urls_to_scrape:
            article_data = self.scrape_single_article(url)
            if article_data:
                article_data["site_name"] = site_name
                article_data["site_domain"] = site_config.get("domain")
                scraped_articles.append(article_data)

        logger.info(
            f"  Successfully scraped {len(scraped_articles)} articles from {site_name}"
        )
        return scraped_articles

    def scrape_all_websites(self, max_articles_per_site: int = 100) -> List[Dict]:
        # This method is the main entry point for scraping all the websites in the
        # configuration file. It is designed to be a high-level workflow that is easy
        # to understand and follow. The use of a `try...except` block is a deliberate
        # choice to make the scraping pipeline more robust to errors on individual sites.
        all_scraped_articles = []

        for site_config in self.sites_to_scrape:
            try:
                articles_from_site = self.scrape_website(
                    site_config, max_articles_per_site
                )
                all_scraped_articles.extend(articles_from_site)

                self._save_articles_to_file(
                    articles_from_site, site_config.get("domain", "unknown")
                )

            except Exception as e:
                logger.error(f"Error scraping {site_config.get('name')}: {e}")
                continue

        logger.info(f"\nTotal articles scraped: {len(all_scraped_articles)}")
        return all_scraped_articles

    def _save_articles_to_file(self, articles: List[Dict], domain: str):
        # This method is responsible for persisting the scraped articles to a file.
        # The choice of appending to the file (`"a"`) is a deliberate one, allowing
        # the scraping process to be incremental and resumable. The use of JSONL
        # format is a good choice for this kind of data, as it is simple, robust,
        # and easy to parse.
        if not articles:
            return

        output_filepath = self.output_directory / f"{domain}_articles.jsonl"

        with output_filepath.open("a", encoding="utf-8") as output_file:
            for article in articles:
                output_file.write(json.dumps(article, ensure_ascii=False) + "\n")

        logger.info(f"  Saved {len(articles)} articles to {output_filepath}")


def main():
    # The `main` function provides a command-line interface for the scraper. This is a
    # standard practice in Python and makes the script more user-friendly and flexible.
    # The use of `argparse` is a deliberate choice to provide a robust and
    # well-documented way to handle command-line arguments.
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

    scraper = ArticleScraper(
        sites_config_filepath=args.sites,
        output_directory=args.output,
        request_delay_seconds=args.delay,
        min_article_word_count=args.min_words,
        min_publication_year=args.min_year,
    )

    articles = scraper.scrape_all_websites(max_articles_per_site=args.max_per_site)

    print("\nSUCCESS: Scraping complete!")
    print(f"   Total articles: {len(articles)}")
    print(f"   Output: {scraper.output_directory}")


if __name__ == "__main__":
    main()
