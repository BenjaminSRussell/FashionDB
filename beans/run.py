"""
Beans - Fashion Rule Extraction Pipeline

Commands:
  scrape <urls_file> <output>       Scrape URLs and extract rules
  distill <results_dir> <output>    Deduplicate and merge rules
  validate <db_file>                Validate rule quality
  filter <db_file> <output>         Filter out invalid rules
  full <urls_file>                  Run full pipeline

Examples:
  python run.py scrape test_urls.txt data/rules.json
  python run.py full test_urls.txt
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

def scrape(urls_file: str, output: str):
    from scrape import Scraper
    urls = [line.strip() for line in Path(urls_file).read_text().split('\n') if line.strip()]
    scraper = Scraper()
    results = scraper.scrape_urls(urls, output)
    print(f"Scraped {len(urls)} URLs: {results['stats']['success']} success, {results['stats']['fail']} fail")
    print(f"Extracted {results['stats']['total_rules']} rules")
    return results

def distill(results_dir: str, output: str):
    from distill import Distiller
    distiller = Distiller(results_dir, output)
    db = distiller.distill()
    stats = db['statistics']
    print(f"Distilled to {stats['total_rules']} unique rules")
    print(f"Domains: {stats['unique_domains']} | Multi-source: {stats['multi_source_percentage']:.1f}%")
    return db

def validate(db_file: str):
    from validate import Validator
    validator = Validator()
    result = validator.validate(db_file)
    print(f"Validated {result['total']} rules: {result['valid']} valid ({result['pass_rate']})")
    if result['sample_issues']:
        print("Sample issues:")
        for issue in result['sample_issues'][:5]:
            print(f"  {issue['text']}... - {issue['error']}")
    return result

def filter_rules(db_file: str, output: str):
    from validate import Validator
    validator = Validator()
    db = validator.filter_invalid(db_file, output)
    print(f"Filtered to {db['statistics']['total_rules']} valid rules")
    print(f"Removed {db['statistics'].get('filtered', 0)} invalid rules")
    return db


def write_run_manifest(manifest: dict, path: str = "data/run_manifest.json") -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote run manifest: {out}")
    return out

def full_pipeline(urls_file: str):
    """New full pipeline flow:
    - If `urls_file` is a path to a file, read URLs from it and scrape them.
    - If `urls_file` looks like a domain (not an existing file), run discovery on the domain to find candidate pages.
    - Extract candidate rules, distill, clean, filter, validate.
    """
    print("=== FULL PIPELINE ===")
    started_at = datetime.now(timezone.utc).isoformat()
    stages: list[dict] = []

    # Determine whether input is a file or a seed domain/URL
    seed = urls_file
    if Path(seed).exists():
        # Read list of URLs from file and use the existing scraper
        print("\n1. SCRAPING (from URL list)")
        scrape(seed, 'data/raw_rules.json')
    else:
        # Treat as domain/seed and run discovery + extraction
        print("\n1. DISCOVERY & EXTRACTION (from domain)")
        from discover_and_extract import DiscoverExtract
        de = DiscoverExtract()
        de.run_domain(seed, out_file='data/raw_rules.json')

    print("\n2. DISTILLING")
    distill('data', 'data/rules_raw.json')

    print("\n3. CLEANING")
    from clean import RuleCleaner, RuleValidationConfig
    # Align with beans/clean.py CLI defaults (5–50 words, quality ≥7).
    # Hardcoding max_word_count=7 rejected almost every natural-language rule.
    clean_cfg = RuleValidationConfig(
        min_word_count=5,
        max_word_count=50,
        min_quality_score=7,
    )
    print(
        f"  clean thresholds: words={clean_cfg.min_word_count}–"
        f"{clean_cfg.max_word_count}, min_quality={clean_cfg.min_quality_score}"
    )
    cleaner = RuleCleaner(clean_cfg)
    cleaner.clean_rules('data/rules_raw.json', 'data/rules_cleaned.json')

    print("\n4. FILTERING")
    filter_rules('data/rules_cleaned.json', 'data/rules.json')

    print("\n5. VALIDATING")
    t0 = time.monotonic()
    result = validate('data/rules.json')
    validate_secs = round(time.monotonic() - t0, 3)
    invalid = 0
    if isinstance(result, dict):
        invalid = int(result.get("invalid") or result.get("invalid_count") or 0)
        if invalid:
            write_run_manifest({
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "input": seed,
                "stages": stages,
                "validate": result,
                "status": "failed",
            })
            raise SystemExit(f"validate failed: {invalid} invalid rules")

    stages.append({"name": "validate", "seconds": validate_secs, "invalid": invalid})
    write_run_manifest({
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "input": seed,
        "stages": stages,
        "outputs": {
            "raw": "data/raw_rules.json",
            "distilled": "data/rules_raw.json",
            "cleaned": "data/rules_cleaned.json",
            "final": "data/rules.json",
        },
        "status": "ok",
    })

    print("\n=== COMPLETE ===")
    print("Final database: data/rules.json")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'scrape' and len(sys.argv) == 4:
        scrape(sys.argv[2], sys.argv[3])
    elif cmd == 'distill' and len(sys.argv) == 4:
        distill(sys.argv[2], sys.argv[3])
    elif cmd == 'validate' and len(sys.argv) == 3:
        validate(sys.argv[2])
    elif cmd == 'filter' and len(sys.argv) == 4:
        filter_rules(sys.argv[2], sys.argv[3])
    elif cmd == 'full' and len(sys.argv) == 3:
        full_pipeline(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()