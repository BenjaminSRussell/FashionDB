"""Create a record-oriented JSON export of Reddit fashion data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Flatten subreddit-scoped Reddit data into a record-oriented JSON file."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DATA_DIR / "reddit_fashion_data.json",
        help="Path to the nested subreddit JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "reddit_fashion_data_unique.json",
        help="Destination for the record-oriented JSON export.",
    )
    parser.add_argument(
        "--skip-deleted",
        action="store_true",
        help="Drop comments whose body is '[deleted]'.",
    )
    return parser.parse_args()


def load_data(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def comment_key(comment: Dict[str, Any]) -> Tuple[str, str]:
    comment_id = str(comment.get("comment_id", "")).strip()
    body = str(comment.get("body", "")).strip()
    return comment_id or "", body


def clean_comments(
    raw_comments: Iterable[Dict[str, Any]],
    skip_deleted: bool,
) -> Tuple[List[Dict[str, Any]], int]:
    unique: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    removed = 0

    for comment in raw_comments:
        if not isinstance(comment, dict):
            removed += 1
            continue

        body = str(comment.get("body", "")).strip()
        if skip_deleted and body == "[deleted]":
            removed += 1
            continue

        key = comment_key(comment)
        if key in seen:
            removed += 1
            continue

        seen.add(key)
        unique.append(comment)

    return unique, removed


def get_top_comment_text(comments: List[Dict[str, Any]]) -> Optional[str]:
    if not comments:
        return None

    top = max(
        comments,
        key=lambda comment: comment.get("score", 0) if isinstance(comment, dict) else 0,
    )
    if not isinstance(top, dict):
        return None

    body = str(top.get("body", "")).strip()
    return body or None


def build_text_field(
    post: Dict[str, Any],
    comments: List[Dict[str, Any]],
) -> str:
    parts: List[str] = []

    title = str(post.get("title", "")).strip()
    if title:
        parts.append(title)

    selftext = str(post.get("selftext", "")).strip()
    if selftext:
        parts.append(selftext)

    top_comment = get_top_comment_text(comments)
    if top_comment:
        parts.append(top_comment)

    return "\n\n".join(parts)


def flatten_posts(
    data: Dict[str, Any],
    skip_deleted: bool,
) -> Tuple[List[Dict[str, Any]], int, int, int]:
    records: List[Dict[str, Any]] = []
    seen_posts: set[Tuple[str, str]] = set()
    total_posts = 0
    removed_posts = 0
    removed_comments = 0

    for subreddit, posts in data.items():
        if not isinstance(posts, list):
            continue

        for post in posts:
            if not isinstance(post, dict):
                continue

            total_posts += 1
            post_id = str(post.get("post_id", "")).strip()
            title = str(post.get("title", "")).strip()
            unique_key = (subreddit, post_id or title)

            if unique_key in seen_posts:
                removed_posts += 1
                continue

            seen_posts.add(unique_key)

            comments_raw = post.get("comments", [])
            cleaned_comments, dropped = clean_comments(
                comments_raw if isinstance(comments_raw, list) else [],
                skip_deleted=skip_deleted,
            )
            removed_comments += dropped

            post_record = {k: v for k, v in post.items() if k != "comments"}
            post_record["comments"] = cleaned_comments
            post_record["subreddit"] = subreddit
            post_record["label"] = subreddit
            post_record["text"] = build_text_field(post_record, cleaned_comments)
            records.append(post_record)

    return records, total_posts, removed_posts, removed_comments


def write_output(path: Path, records: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()

    print(f"Reading data from {args.input}...")
    dataset = load_data(args.input)

    print("Creating record-oriented export...")
    records, total, removed_posts, removed_comments = flatten_posts(
        dataset,
        skip_deleted=args.skip_deleted,
    )

    print(f"Total posts processed: {total}")
    print(f"Duplicate posts removed: {removed_posts}")
    print(f"Duplicate comments removed: {removed_comments}")
    print(f"Records retained: {len(records)}")

    print(f"Writing {len(records)} records to {args.output}...")
    write_output(args.output, records)
    print("Done.")


if __name__ == "__main__":
    main()
