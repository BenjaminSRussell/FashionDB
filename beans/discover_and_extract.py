"""Discovery + extraction pipeline

- Discover candidate pages within a domain (look for path keywords like guide, rules, how, do, dont, tips)
- Fetch pages with browser-like headers and polite delays
- Extract candidate rule texts from article blocks, lists (ol/ul/li), and numbered sentences
- Use sentence-transformer embeddings for a zero-shot-like classification: compare against a "rule" prototype and a "promo" prototype
- Standardize selected candidates into rule objects: rule_text, rule_type, quality_score, word_count, sources

This module intentionally avoids heavy LLM calls and uses deterministic heuristics + embeddings for classification and standardization.
"""

from typing import List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
except Exception:
    SentenceTransformer = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_KEYWORDS = ["guide", "rules", "how", "do", "dont", "tips", "tutorial", "etiquette", "fit", "style", "ways", "ways-to", "dos-and-donts"]

class DiscoverExtract:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', max_pages: int = 80, delay: float = 0.5):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })
        self.max_pages = max_pages
        self.delay = delay
        self.model = None
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded sentence-transformer model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformer model: {e}")
                self.model = None

        # Precompute prototypes
        self.rule_proto = "This is a concrete, actionable fashion rule about how to wear or combine clothing."
        self.promo_proto = "This is promotional text, or navigational or call-to-action, not a specific rule."
        self.rule_emb = None
        self.promo_emb = None
        if self.model:
            self.rule_emb = self.model.encode([self.rule_proto])[0]
            self.promo_emb = self.model.encode([self.promo_proto])[0]

    def discover_urls_from_domain(self, seed: str, keywords: List[str] = None) -> List[str]:
        """Discover candidate URLs within the same domain that contain keywords in path or subdomain."""
        keywords = keywords or DEFAULT_KEYWORDS
        parsed = urlparse(seed if seed.startswith('http') else f'https://{seed}')
        base = f"{parsed.scheme}://{parsed.netloc}"
        to_visit = [base]
        seen: Set[str] = set()
        candidates: List[str] = []

        while to_visit and len(seen) < self.max_pages:
            url = to_visit.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Find links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full = urljoin(base, href)
                    p = urlparse(full)
                    if p.netloc != parsed.netloc:
                        continue
                    path = p.path.lower()
                    # If path or subdomain contains keywords, add to candidates
                    if any(k in path for k in keywords) or any(k in p.netloc for k in keywords):
                        if full not in candidates:
                            candidates.append(full)
                    # enqueue for crawl if not deep
                    if full not in seen and full not in to_visit and len(seen) + len(to_visit) < self.max_pages:
                        to_visit.append(full)
            except Exception as e:
                logger.debug(f"Error discovering {url}: {e}")
                continue
        logger.info(f"Discovered {len(candidates)} candidate pages on {parsed.netloc}")
        return candidates

    def fetch_page(self, url: str) -> str:
        try:
            time.sleep(self.delay)
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.text
            logger.debug(f"Non-200 {resp.status_code} for {url}")
        except Exception as e:
            logger.debug(f"Fetch failed {url}: {e}")
        return ""

    def extract_candidates(self, html: str, source: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        # remove scripts/styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'iframe']):
            tag.decompose()

        # try article-like blocks
        content = None
        for selector in ['article', '.article', '.post-content', '.entry-content', '.content', 'main']:
            el = soup.select_one(selector)
            if el:
                content = el
                break
        if content is None:
            content = soup.body or soup

        candidates: List[Dict[str, Any]] = []
        # lists (ol, ul)
        for li in content.select('ol li, ul li'):
            text = ' '.join(li.stripped_strings)
            if len(text) > 20:
                candidates.append({'text': text, 'source': source})
        # numbered sentences: lines starting with digits or bullet patterns
        for p in content.find_all(['p', 'li']):
            line = ' '.join(p.stripped_strings)
            # look for numbered start or bullet-like
            if re.match(r'^(\d+\.|\d+\))\s+', line) and len(line) > 30:
                # split on numbered prefixes
                parts = re.split(r'\d+\.|\d+\)', line)
                for part in parts:
                    t = part.strip()
                    if len(t) > 30:
                        candidates.append({'text': t, 'source': source})
            elif len(line) > 60 and any(w in line.lower() for w in ['should', 'never', 'always', 'avoid', 'must']):
                candidates.append({'text': line, 'source': source})

        # dedupe by text
        seen_texts = set()
        filtered = []
        for c in candidates:
            t = c['text'].strip()
            if t in seen_texts:
                continue
            seen_texts.add(t)
            filtered.append(c)
        return filtered

    def is_fashion_rule(self, texts: List[str], threshold: float = 0.55) -> List[bool]:
        """Classify each text as rule or not using embedding similarity to prototype."""
        if not self.model or self.rule_emb is None:
            # fallback: keyword+indicator based
            results = []
            for t in texts:
                tl = t.lower()
                ok = any(word in tl for word in ['should', 'never', 'always', 'avoid', 'must', 'match', 'pair', 'choose']) and any(word in tl for word in ['suit','jacket','tie','belt','shoes','shirt','pants','match','fit','lapel','sleeve','cuff'])
                results.append(ok)
            return results

        emb = self.model.encode(texts)
        # cosine with rule and promo
        sim_rule = cosine_similarity(emb, self.rule_emb.reshape(1, -1)).reshape(-1)
        sim_promo = cosine_similarity(emb, self.promo_emb.reshape(1, -1)).reshape(-1)
        results = [(r > threshold and r > p) for r, p in zip(sim_rule, sim_promo)]
        return results

    def standardize(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize accepted candidate texts into rule objects"""
        outputs = []
        texts_only = [t['text'] for t in texts]
        if self.model:
            emb_texts = self.model.encode(texts_only)
            rule_proto_emb = self.rule_emb
        else:
            emb_texts = None
            rule_proto_emb = None

        for i, cand in enumerate(texts):
            text = cand['text'].strip()
            # type detection via keywords
            tl = text.lower()
            if any(k in tl for k in ['fit','sleeve','hem','cuff','waist','size','length']):
                rtype = 'fit'
            elif any(k in tl for k in ['color','colour','match','contrast','brown','black']):
                rtype = 'color'
            elif any(k in tl for k in ['accessor','belt','tie','watch','shoe']):
                rtype = 'accessories'
            elif any(k in tl for k in ['formal','casual','dress code']):
                rtype = 'formality'
            elif any(k in tl for k in ['style','trend','fashion','pair','combine']):
                rtype = 'style'
            else:
                rtype = 'general'

            # quality scoring heuristic
            score = 5
            wc = len(text.split())
            if wc >= 8:
                score += 2
            if emb_texts is not None:
                sim = float(cosine_similarity(emb_texts[i].reshape(1, -1), rule_proto_emb.reshape(1, -1))[0][0])
                score += int(round(sim * 3))
            score = max(1, min(10, score))

            outputs.append({
                'rule_text': text,
                'rule_type': rtype,
                'quality_score': score,
                'word_count': wc,
                'sources': [{'url': cand['source'], 'domain': urlparse(cand['source']).netloc}],
                'source_count': 1
            })
        return outputs

    def run_domain(self, seed: str, out_file: str = None) -> Dict[str, Any]:
        """Run discovery+extraction on a single domain and return a structured rules dict."""
        candidates_urls = self.discover_urls_from_domain(seed)
        # if discovery found nothing, try the seed itself
        if not candidates_urls:
            candidates_urls = [seed if seed.startswith('http') else f'https://{seed}']

        all_candidates = []
        for u in candidates_urls[:self.max_pages]:
            html = self.fetch_page(u)
            if not html:
                continue
            cands = self.extract_candidates(html, u)
            logger.info(f"Extracted {len(cands)} candidates from {u}")
            all_candidates.extend(cands)

        # classify
        texts = [c['text'] for c in all_candidates]
        is_rule_mask = self.is_fashion_rule(texts)
        selected = [c for c, ok in zip(all_candidates, is_rule_mask) if ok]
        logger.info(f"Selected {len(selected)} rules from {len(all_candidates)} candidates")

        # standardize
        rules = self.standardize(selected)

        out = {
            'rules': rules,
            'statistics': {
                'total_rules': len(rules),
                'unique_domains': len(set(urlparse(r['sources'][0]['url']).netloc for r in rules)),
                'domains': list(set(urlparse(r['sources'][0]['url']).netloc for r in rules)),
                'rule_types': {},
                'multi_source_rules': 0,
                'multi_source_percentage': 0.0,
                'avg_quality_score': (sum(r['quality_score'] for r in rules) / len(rules)) if rules else 0,
                'avg_word_count': (sum(r['word_count'] for r in rules) / len(rules)) if rules else 0,
                'completeness_rate': 100.0
            }
        }
        # count types
        type_counts = {}
        for r in rules:
            type_counts[r['rule_type']] = type_counts.get(r['rule_type'], 0) + 1
        out['statistics']['rule_types'] = type_counts

        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            Path(out_file).write_text(json.dumps(out, indent=2))
            logger.info(f"Saved discovery results to {out_file}")

        return out


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument('seed', help='Domain or seed URL to discover')
    parser.add_argument('--out', '-o', help='Output file for discovered rules', default='data/discovered_rules.json')
    args = parser.parse_args()
    de = DiscoverExtract()
    res = de.run_domain(args.seed, args.out)
    print(json.dumps(res, indent=2))
