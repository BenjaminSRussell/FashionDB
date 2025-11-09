"""Beans - Fashion Rule Extraction Pipeline

Usage:
    python run.py scrape <urls_file> <output_file>
        Scrape fashion rules from URLs listed in urls_file

    python run.py distill <results_dir> <output_file>
        Distill and deduplicate scraped rules

    python run.py validate <db_file>
        Validate rules in the database file

    python run.py filter <db_file> <output_file>
        Filter out invalid rules and save to output

    python run.py full <urls_file>
        Run the complete pipeline: scrape -> distill -> filter -> validate

Examples:
    python run.py scrape urls.txt data/raw_rules.json
    python run.py full urls.txt
"""

import sys
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
    stats = db.get('statistics', {})
    total = stats.get('total_rules', len(db.get('rules', [])))
    filtered = stats.get('filtered', 0)
    print(f"Filtered to {total} valid rules")
    print(f"Removed {filtered} invalid rules")
    return db

def full_pipeline(urls_file: str):
    print("=== FULL PIPELINE ===")
    print("\n1. SCRAPING")
    scrape(urls_file, 'data/raw_rules.json')

    print("\n2. DISTILLING")
    distill('data', 'data/rules_raw.json')

    print("\n3. FILTERING")
    filter_rules('data/rules_raw.json', 'data/rules.json')

    print("\n4. VALIDATING")
    validate('data/rules.json')

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