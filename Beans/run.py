import sys
import json
import logging
from pathlib import Path
import argparse

# Add src to the path so local modules can be imported.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper import ArticleScraper
from src.rules_extractor_v2 import EnhancedRulesExtractor
from src.goldset_builder_v2 import UnbiasedGoldSetBuilder


def configure_logging(enable_debug_mode: bool = False):
    # Configure logging for normal or debug output.
    log_level = logging.DEBUG if enable_debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def execute_scrape_command(args):
    # Run article scraping.
    print("\n" + "=" * 80)
    print("SCRAPING ARTICLES")
    print("=" * 80)

    article_scraper = ArticleScraper(
        sites_config_filepath=args.sites_config,
        output_directory=args.raw_data_directory,
        request_delay_seconds=args.request_delay,
        min_article_word_count=args.min_word_count,
        min_publication_year=args.min_publication_year,
    )

    articles = article_scraper.scrape_all_websites(
        max_articles_per_site=args.max_articles_per_site
    )

    print("\nSUCCESS: Scraping complete!")
    print(f"   Total articles: {len(articles)}")
    print(f"   Output: {article_scraper.output_dir}")

    return articles


def execute_extract_command(args):
    # Extract rules from saved articles.
    print("\n" + "=" * 80)
    print("EXTRACTING RULES")
    print("=" * 80)

    rules_extractor = EnhancedRulesExtractor(
        input_directory=args.raw_data_directory,
        output_directory=args.processed_data_directory,
        min_rule_character_length=args.min_rule_length,
        max_rule_character_length=args.max_rule_length,
    )

    stats = rules_extractor.process_all_files()

    print("\nSUCCESS: Extraction complete!")
    print(f"   Rules extracted: {stats['rules_extracted']}")
    print(f"   Articles processed: {stats['articles_processed']}")
    print(f"   Output: {rules_extractor.output_directory}")

    return stats


def execute_full_pipeline(args):
    # Run scrape and extraction end to end.
    print("\n" + "=" * 80)
    print("FULL PIPELINE")
    print("=" * 80)

    articles = execute_scrape_command(args)

    if not articles:
        print("\nWARNING:  No articles scraped. Exiting.")
        return

    stats = execute_extract_command(args)

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Articles scraped: {len(articles)}")
    print(f"Rules extracted: {stats['rules_extracted']}")


def execute_stats_command(args):
    # Show counts for saved article and rule files.
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    raw_dir = Path(args.raw_data_directory)
    article_files = list(raw_dir.glob("*_articles.jsonl"))

    total_article_count = 0
    for article_path in article_files:
        with article_path.open("r") as article_file:
            article_count = sum(1 for line in article_file if line.strip())
            total_article_count += article_count
            print(f"  {article_path.name}: {article_count} articles")

    print(f"\nTotal raw articles: {total_article_count}")

    processed_dir = Path(args.processed_data_directory)
    rules_path = processed_dir / "rules.jsonl"

    if rules_path.exists():
        with rules_path.open("r") as rules_file:
            rule_count = sum(1 for line in rules_file if line.strip())
        print(f"Total rules: {rule_count}")

        rules_by_category = {}
        with rules_path.open("r") as rules_file:
            for line in rules_file:
                if line.strip():
                    try:
                        rule_entry = json.loads(line)
                        rule_category = rule_entry.get("category", "unknown")
                        rules_by_category[rule_category] = (
                            rules_by_category.get(rule_category, 0) + 1
                        )
                    except:
                        pass

        print("\nRules by category:")
        for category, count in sorted(
            rules_by_category.items(), key=lambda item: item[1], reverse=True
        ):
            print(f"  {category}: {count}")
    else:
        print(f"\nNo rules file found at {rules_path}")


def execute_goldset_command(args):
    # Build a labeled sampling set.
    print("\n" + "=" * 80)
    print("BUILDING GOLD SET")
    print("=" * 80)

    if args.gold_set_max_articles is not None:
        logging.warning(
            "gold_set_max_articles is deprecated and ignored by the unbiased sampler."
        )

    goldset_builder = UnbiasedGoldSetBuilder(
        input_directory=args.raw_data_directory,
        output_filepath=args.gold_set_output_filepath,
        target_dataset_size=args.gold_set_target_size,
        min_sentence_length_chars=args.gold_set_min_sentence_length,
        max_sentence_length_chars=args.gold_set_max_sentence_length,
        samples_per_source=args.gold_set_per_site,
        random_seed=args.gold_set_random_seed,
    )

    goldset_summary = goldset_builder.build_gold_set()

    print("\n" + "=" * 80)
    print("GOLD SET SUMMARY")
    print("=" * 80)
    print(f"Articles loaded:     {goldset_summary['articles_loaded']}")
    print(
        f"Sentences extracted: {goldset_summary['total_sentences_extracted']}"
    )
    print(
        f"Sentences selected:  {goldset_summary['sentences_selected']}"
    )
    print(f"Sampling method:     {goldset_summary['sampling_method']}")
    print(f"Bias:                {goldset_summary['bias']}")
    print(f"Output file:         {goldset_summary['output_path']}")


def execute_clean_command(args):
    # Ask for confirmation before deleting data.
    import shutil

    print("\nWARNING:  WARNING: This will delete all data!")
    confirmation = input("Are you sure? (yes/no): ")

    if confirmation.lower() != "yes":
        print("Cancelled.")
        return

    raw_dir = Path(args.raw_data_directory)
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        print(f"SUCCESS: Deleted {raw_dir}")

    processed_dir = Path(args.processed_data_directory)
    if processed_dir.exists():
        shutil.rmtree(processed_dir)
        print(f"SUCCESS: Deleted {processed_dir}")

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("\nSUCCESS: Data directories cleaned and recreated")


def main():
    # Parse CLI arguments and run the requested command.
    parser = argparse.ArgumentParser(
        description="Fashion Rules Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py all                      # Run full pipeline
  python run.py scrape --max-per-site 50 # Scrape up to 50 articles per site
  python run.py extract                  # Extract rules from scraped articles
  python run.py stats                    # Show statistics
  python run.py clean                    # Clean all data
        """,
    )

    parser.add_argument(
        "command",
        choices=["scrape", "extract", "all", "stats", "clean", "goldset"],
        help="Command to run",
    )

    parser.add_argument(
        "--sites-config", default="sites.jsonl", help="Sites config file"
    )
    parser.add_argument(
        "--raw-data-directory", default="data/raw", help="Raw articles directory"
    )
    parser.add_argument(
        "--processed-data-directory",
        default="data/processed",
        help="Processed rules directory",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    parser.add_argument(
        "--max-articles-per-site",
        type=int,
        default=50,
        help="Max articles per site",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.0,
        help="Delay between requests (seconds)",
    )
    parser.add_argument(
        "--min-word-count", type=int, default=300, help="Minimum word count"
    )
    parser.add_argument(
        "--min-publication-year",
        type=int,
        default=2015,
        help="Minimum publication year",
    )

    parser.add_argument(
        "--min-rule-length", type=int, default=30, help="Minimum rule length"
    )
    parser.add_argument(
        "--max-rule-length", type=int, default=500, help="Maximum rule length"
    )

    parser.add_argument(
        "--gold-set-output-filepath",
        default="data/processed/gold_set.jsonl",
        help="Output JSONL file for manual labeling",
    )
    parser.add_argument(
        "--gold-set-target-size",
        type=int,
        default=800,
        help="Total number of sentences to include in the gold set",
    )
    parser.add_argument(
        "--gold-set-max-articles",
        type=int,
        default=None,
        help="(Deprecated) Former article cap; ignored by unbiased builder",
    )
    parser.add_argument(
        "--gold-set-per-site",
        type=int,
        default=None,
        help="Optional per-site cap when sampling sentences",
    )
    parser.add_argument(
        "--gold-set-min-sentence-length",
        type=int,
        default=25,
        help="Minimum sentence length for inclusion",
    )
    parser.add_argument(
        "--gold-set-max-sentence-length",
        type=int,
        default=350,
        help="Maximum sentence length for inclusion",
    )
    parser.add_argument(
        "--gold-set-random-seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling",
    )

    args = parser.parse_args()

    configure_logging(args.debug)

    command_map = {
        "scrape": execute_scrape_command,
        "extract": execute_extract_command,
        "all": execute_full_pipeline,
        "stats": execute_stats_command,
        "clean": execute_clean_command,
        "goldset": execute_goldset_command,
    }

    try:
        command_map[args.command](args)
    except KeyboardInterrupt:
        print("\n\nWARNING:  Interrupted by user")
        sys.exit(1)
    except Exception as error:
        print(f"\nERROR: Error: {error}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
