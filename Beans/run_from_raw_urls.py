"""Run discovery+extraction against entries in data/raw_urls/raw_urls.json

Behavior:
- Read NDJSON file where each line is a JSON object describing a source (as in your raw_urls.json)
- Select active entries, sort by priority (desc), take top N (configurable)
- For each, run DiscoverExtract.run_domain and collect results
- Aggregate into data/raw_rules.json
- Run the cleaner to produce data/rules_cleaned.json

This is a cautious runner; it respects the per-domain `delay` value and limits concurrent requests.
"""

import json
from pathlib import Path
from time import sleep
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URLS_PATH = Path('data/raw_urls/raw_urls.json')
OUT_RAW_RULES = Path('data/raw_rules.json')
OUT_CLEANED = Path('data/rules_cleaned.json')

TOP_N = 10


def load_raw_sources(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    entries = []
    with path.open('r') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                entries.append(obj)
            except Exception as e:
                logger.warning(f"Failed to parse line in {path}: {e}")
    return entries


def aggregate_results(results_list):
    all_rules = []
    domains = set()
    for res in results_list:
        rules = res.get('rules', [])
        all_rules.extend(rules)
        domains.update(res.get('statistics', {}).get('domains', []))
    stats = {
        'total_rules': len(all_rules),
        'unique_domains': len(domains),
        'domains': sorted(list(domains)),
    }
    return {'rules': all_rules, 'statistics': stats}


def main(top_n=TOP_N):
    from discover_and_extract import DiscoverExtract
    from clean import RuleCleaner, RuleValidationConfig

    sources = load_raw_sources(RAW_URLS_PATH)
    active = [s for s in sources if s.get('active', True)]
    sorted_src = sorted(active, key=lambda s: s.get('priority', 0), reverse=True)
    selected = sorted_src[:top_n]
    logger.info(f"Selected {len(selected)} sources (top {top_n}) for discovery")

    de = DiscoverExtract()
    aggregated = []
    for src in selected:
        domain = src.get('domain')
        seed_urls = src.get('urls', [])
        # prefer using the first provided url as seed
        seed = seed_urls[0] if seed_urls else domain
        logger.info(f"Running discovery for: {src.get('name')} ({domain}) seed={seed}")
        # apply per-domain delay if present
        delay = src.get('delay', 1.0)
        de.delay = max(de.delay, float(delay))
        res = de.run_domain(seed)
        aggregated.append(res)
        # be polite between domains
        sleep(delay)

    out = aggregate_results(aggregated)
    OUT_RAW_RULES.parent.mkdir(parents=True, exist_ok=True)
    OUT_RAW_RULES.write_text(json.dumps(out, indent=2))
    logger.info(f"Wrote aggregated raw rules to {OUT_RAW_RULES}")

    # Run cleaner
    cleaner = RuleCleaner(RuleValidationConfig(min_word_count=5, max_word_count=80, min_quality_score=5))
    cleaned = cleaner.clean_rules(str(OUT_RAW_RULES), str(OUT_CLEANED))
    logger.info(f"Cleaning complete, cleaned rules at {OUT_CLEANED}")

    print(json.dumps({'aggregated': out['statistics'], 'cleaned': cleaned['statistics']}, indent=2))


if __name__ == '__main__':
    main()
