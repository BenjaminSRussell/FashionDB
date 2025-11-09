import requests
import json
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from extract import Extractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Scraper:
    def __init__(self, config_path='config/extraction_rules.json', workers=4):
        self.cfg = json.loads(Path(config_path).read_text()) if Path(config_path).exists() else {'sites': {}}
        self.ext = Extractor()
        self.workers = workers
        self.session = requests.Session()

    def scrape_urls(self, urls: list, output: str) -> dict:
        results = {'rules': [], 'stats': {'success': 0, 'fail': 0}}

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._scrape_url, url): url for url in urls}
            for future in as_completed(futures):
                try:
                    rules = future.result()
                    if rules:
                        results['rules'].extend(rules)
                        results['stats']['success'] += 1
                    else:
                        results['stats']['fail'] += 1
                except Exception as e:
                    url = futures[future]
                    logging.error(f"Failed to process {url}: {e}")
                    results['stats']['fail'] += 1

        results['stats']['total_rules'] = len(results['rules'])
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(results, indent=2))
        return results

    def _scrape_url(self, url: str) -> list:
        try:
            resp = self.session.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code != 200:
                logging.warning(f"HTTP {resp.status_code} for {url}")
                return []
            text = self._extract_text(resp.text)
            rules = self.ext.extract(text)
            return [{**r, 'sources': [{'url': url, 'domain': self._domain(url)}]} for r in rules]
        except requests.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            return []

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
            tag.decompose()
        return ' '.join(soup.stripped_strings)

    def _domain(self, url: str) -> str:
        return url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'