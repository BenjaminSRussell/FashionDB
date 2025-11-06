import json
import praw
import prawcore
import configparser
import signal
import sys
import atexit
from pathlib import Path
from datetime import datetime



class ScraperConfig:
    # Core settings for the Reddit scraper.
    MIN_POST_SCORE: int = 15
    MIN_COMMENT_SCORE: int = 10
    POST_LIMIT: int = 0  # 0 for no limit (up to 1000)
    TIME_FILTER: str = "all"  # "all", "year", "month", etc.

    BASE_DIR: Path = Path(__file__).resolve().parent
    CONFIG_PATH: Path = BASE_DIR.parent / "config" / "config.ini"
    OUTPUT_DIR: Path = BASE_DIR.parent / "data"
    OUTPUT_FILENAME: Path = OUTPUT_DIR / "reddit_fashion_data.json"
    TARGET_SUBREDDITS_PATH: Path = BASE_DIR / "target_subreddits.json"
    SEARCH_QUERIES_PATH: Path = BASE_DIR / "search_queries.json"

_active_scrape_data = {}
_save_attempts = 0
_processed_post_count = 0


def read_json_data(path: Path, expected_type):
    # Load JSON into the expected type, defaulting to empty values on error.
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            parsed_data = json.load(file_handle)
    except FileNotFoundError:
        print(f"Warning: {path} not found. Using empty {expected_type.__name__}.")
        return expected_type()
    except json.JSONDecodeError as exc:
        print(f"Warning: Failed to parse {path}: {exc}. Using empty {expected_type.__name__}.")
        return expected_type()

    if not isinstance(parsed_data, expected_type):
        print(f"Warning: {path} does not contain a {expected_type.__name__}. Using empty fallback.")
        return expected_type()

    return parsed_data


def create_search_query_map(raw_queries: dict) -> dict:
    # Convert loose query definitions into PRAW search strings.
    query_map: dict[str, str] = {}
    for query_name, raw_entry in raw_queries.items():
        if isinstance(raw_entry, list):
            raw_terms = [str(term).strip() for term in raw_entry if isinstance(term, str) and term.strip()]
            if not raw_terms:
                print(f"Warning: Query '{query_name}' has no valid terms. Skipping.")
                continue
            formatted_terms = []
            for term in raw_terms:
                escaped_term = term.replace('"', '\\"')
                formatted_terms.append(f'title:"{escaped_term}"')
            query_map[query_name] = " OR ".join(formatted_terms)
        elif isinstance(raw_entry, str) and raw_entry.strip():
            query_map[query_name] = raw_entry.strip()
        else:
            print(f"Warning: Query '{query_name}' has unsupported format ({type(raw_entry).__name__}). Skipping.")
    return query_map


# Load configuration data at module level
TARGET_SUBREDDITS: list = read_json_data(ScraperConfig.TARGET_SUBREDDITS_PATH, list)
RAW_SEARCH_QUERIES: dict = read_json_data(ScraperConfig.SEARCH_QUERIES_PATH, dict)
SEARCH_QUERIES: dict = create_search_query_map(RAW_SEARCH_QUERIES)


def write_scrape_data(scrape_snapshot: dict, target_path: Path, save_label: str = "regular"):
    # Persist scraping progress, keeping a backup of the last file.
    global _save_attempts
    try:
        if target_path.exists():
            backup_path = target_path.with_suffix('.json.backup')
            target_path.rename(backup_path)

        with open(target_path, 'w', encoding='utf-8') as output_file:
            json.dump(scrape_snapshot, output_file, indent=4, ensure_ascii=False)

        _save_attempts += 1
        total_posts = sum(len(posts) for posts in scrape_snapshot.values())
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {save_label.upper()} SAVE #{_save_attempts}: {total_posts} total posts from {len(scrape_snapshot)} subreddits saved to {target_path}")
        return True
    except Exception as error:
        print(f"\n!!! ERROR saving data: {error}")
        try:
            emergency_path = target_path.with_name(f"emergency_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(emergency_path, 'w', encoding='utf-8') as emergency_file:
                json.dump(scrape_snapshot, emergency_file, indent=4, ensure_ascii=False)
            print(f"Emergency save successful: {emergency_path}")
            return True
        except Exception as emergency_error:
            print(f"!!! CRITICAL: Emergency save failed: {emergency_error}")
            return False


def handle_emergency_shutdown(signal_number=None, frame=None):
    # Save progress before exiting when interrupted.
    print("\n\n" + "="*60)
    print("INTERRUPT DETECTED - SAVING DATA SAFELY...")
    print("="*60)

    if _active_scrape_data:
        if write_scrape_data(_active_scrape_data, ScraperConfig.OUTPUT_FILENAME, save_label="emergency"):
            total_posts = sum(len(posts) for posts in _active_scrape_data.values())
            print(f"\nSafely saved {total_posts} posts from {len(_active_scrape_data)} subreddits")
            print(f"Total saves this session: {_save_attempts}")
            print(f"Posts processed this session: {_processed_post_count}")
        else:
            print("\n!!! WARNING: Save may have failed. Check emergency_save_*.json files.")
    else:
        print("No data to save.")

    print("\nExiting gracefully...")
    sys.exit(0)


def create_reddit_client():
    # Create a Reddit client using credentials from config.ini.
    config_parser = configparser.ConfigParser()
    if not ScraperConfig.CONFIG_PATH.exists():
        print(f"Error: Configuration file not found at {ScraperConfig.CONFIG_PATH}.")
        return None

    config_parser.read(ScraperConfig.CONFIG_PATH)

    try:
        creds = config_parser["DEFAULT"]
        reddit = praw.Reddit(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            username=creds["username"],
            password=creds["password"],
            user_agent=creds["user_agent"],
        )
        user = reddit.user.me()
        print(f"Authenticated as u/{user.name}")
        return reddit
    except (KeyError, Exception) as e:
        print(f"Authentication failed: {e}")
        return None
    

def read_existing_data(filepath: Path) -> dict:
    # Load any prior scrape output for incremental updates.
    if not filepath.exists():
        print("No existing data file found. Starting fresh.")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as existing_file:
            stored_data = json.load(existing_file)
        total_posts = sum(len(posts) for posts in stored_data.values())
        print(f"Loaded {total_posts} existing posts from {len(stored_data)} subreddits")
        return stored_data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {filepath}: {e}. Starting fresh.")
        return {}
    
def main():
    global _active_scrape_data, _processed_post_count

    signal.signal(signal.SIGINT, handle_emergency_shutdown)
    signal.signal(signal.SIGTERM, handle_emergency_shutdown)
    atexit.register(handle_emergency_shutdown)

    print("Reddit Fashion Scraper")
    print("Press Ctrl+C to save and exit.")

    reddit = create_reddit_client()
    if not reddit:
        return

    if not TARGET_SUBREDDITS:
        print(f"Error: No target subreddits loaded from {ScraperConfig.TARGET_SUBREDDITS_PATH}.")
        return

    if not SEARCH_QUERIES:
        print(f"Error: No search queries loaded from {ScraperConfig.SEARCH_QUERIES_PATH}.")
        return

    ScraperConfig.OUTPUT_DIR.mkdir(exist_ok=True)

    all_scraped_data = read_existing_data(ScraperConfig.OUTPUT_FILENAME)
    _active_scrape_data = all_scraped_data

    try:
        for subreddit_name in TARGET_SUBREDDITS:
            print(f"\n--- Scraping r/{subreddit_name} ---")

            try:
                subreddit = reddit.subreddit(subreddit_name)
                _ = subreddit.id  # Verify subreddit exists
            except (prawcore.exceptions.Redirect, prawcore.exceptions.Forbidden, prawcore.exceptions.PrawcoreException) as e:
                print(f"  [!] Skipping r/{subreddit_name}: {e}")
                continue

            if subreddit_name not in all_scraped_data:
                all_scraped_data[subreddit_name] = []

            saved_posts = all_scraped_data[subreddit_name]
            known_post_ids = {post["post_id"] for post in saved_posts}

            new_posts_count = 0

            for query_name, query_string in SEARCH_QUERIES.items():
                print(f"\n  [Query: {query_name}]")

                try:
                    search_results = subreddit.search(
                        query=query_string,
                        sort="top",
                        time_filter=ScraperConfig.TIME_FILTER,
                        limit=ScraperConfig.POST_LIMIT or None
                    )
                except prawcore.exceptions.PrawcoreException as e:
                    print(f"    [!] Search failed: {e}")
                    continue

                for submission in search_results:
                    if submission.id in known_post_ids or submission.score < ScraperConfig.MIN_POST_SCORE:
                        continue

                    print(f"  [+] Processing: {submission.title[:60]}... (Score: {submission.score})")
                    new_posts_count += 1
                    _processed_post_count += 1

                    post_data = {
                        "post_id": submission.id,
                        "title": submission.title,
                        "score": submission.score,
                        "url": f"https://reddit.com{submission.permalink}",
                        "flair": submission.link_flair_text,
                        "selftext": submission.selftext,
                        "comments": []
                    }

                    submission.comment_sort = "top"
                    submission.comments.replace_more(limit=0)

                    saved_comment_count = 0
                    for comment in submission.comments.list():
                        if comment.score >= ScraperConfig.MIN_COMMENT_SCORE:
                            post_data["comments"].append({
                                "comment_id": comment.id,
                                "body": comment.body,
                                "score": comment.score
                            })
                            saved_comment_count += 1

                    print(f"      -> Saved {saved_comment_count} comments.")
                    saved_posts.append(post_data)
                    known_post_ids.add(submission.id)

            print(f"\n--- Finished r/{subreddit_name}: Found {new_posts_count} new posts. Total: {len(saved_posts)} ---")
            write_scrape_data(all_scraped_data, ScraperConfig.OUTPUT_FILENAME, save_label="auto")

        write_scrape_data(all_scraped_data, ScraperConfig.OUTPUT_FILENAME, save_label="final")

        total_posts = sum(len(posts) for posts in all_scraped_data.values())
        print(f"\nSCRAPING COMPLETE: Saved {total_posts} posts from {len(all_scraped_data)} subreddits to {ScraperConfig.OUTPUT_FILENAME}")

    except KeyboardInterrupt:
        handle_emergency_shutdown()
    except Exception as e:
        print(f"\n\nCRITICAL ERROR: {e}")
        print("Attempting to save data...")
        if _active_scrape_data:
            if write_scrape_data(_active_scrape_data, ScraperConfig.OUTPUT_FILENAME, save_label="crash"):
                print("Data saved successfully!")
            else:
                print("Save failed. Check emergency_save_*.json files.")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
