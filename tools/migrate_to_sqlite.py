#!/usr/bin/env python3
"""
SQLite Database Migration Script
Migrates Reddit fashion data from JSON to SQLite database.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict


def create_database_schema(conn: sqlite3.Connection):
    """Create the database schema."""
    print("Creating database schema...")

    cursor = conn.cursor()

    # Posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            score INTEGER,
            url TEXT,
            flair TEXT,
            selftext TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Comments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            body TEXT NOT NULL,
            score INTEGER,
            FOREIGN KEY (post_id) REFERENCES posts(post_id)
        )
    """)

    # Query metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            posts_found INTEGER,
            avg_post_score REAL,
            rules_extracted INTEGER,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Subreddit stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subreddit_stats (
            subreddit TEXT PRIMARY KEY,
            total_posts INTEGER DEFAULT 0,
            avg_post_score REAL DEFAULT 0,
            total_comments INTEGER DEFAULT 0,
            last_scraped TIMESTAMP
        )
    """)

    # Create indexes
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_score ON posts(score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_score ON comments(score)")

    conn.commit()
    print("Schema created successfully!")


def migrate_data(conn: sqlite3.Connection, data: Dict):
    """Migrate data from JSON to SQLite."""
    cursor = conn.cursor()

    total_posts = 0
    total_comments = 0

    print("\nMigrating data...")
    print("-" * 60)

    for subreddit, posts in data.items():
        print(f"Processing r/{subreddit}... ", end='', flush=True)

        subreddit_posts = 0
        subreddit_comments = 0
        subreddit_total_score = 0

        for post in posts:
            # Insert post
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO posts
                    (post_id, subreddit, title, score, url, flair, selftext)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    post.get('post_id'),
                    subreddit,
                    post.get('title', ''),
                    post.get('score', 0),
                    post.get('url', ''),
                    post.get('flair', ''),
                    post.get('selftext', '')
                ))

                subreddit_posts += 1
                total_posts += 1
                subreddit_total_score += post.get('score', 0)

                # Insert comments
                for comment in post.get('comments', []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO comments
                        (comment_id, post_id, body, score)
                        VALUES (?, ?, ?, ?)
                    """, (
                        comment.get('comment_id'),
                        post.get('post_id'),
                        comment.get('body', ''),
                        comment.get('score', 0)
                    ))
                    subreddit_comments += 1
                    total_comments += 1

            except sqlite3.Error as e:
                print(f"\nError inserting post {post.get('post_id')}: {e}", file=sys.stderr)
                continue

        # Update subreddit stats
        avg_score = subreddit_total_score / subreddit_posts if subreddit_posts > 0 else 0
        cursor.execute("""
            INSERT OR REPLACE INTO subreddit_stats
            (subreddit, total_posts, avg_post_score, total_comments, last_scraped)
            VALUES (?, ?, ?, ?, ?)
        """, (
            subreddit,
            subreddit_posts,
            avg_score,
            subreddit_comments,
            datetime.now().isoformat()
        ))

        print(f"{subreddit_posts} posts, {subreddit_comments} comments")

    conn.commit()

    print("-" * 60)
    print(f"\nMigration complete!")
    print(f"Total posts: {total_posts}")
    print(f"Total comments: {total_comments}")


def generate_migration_report(conn: sqlite3.Connection, output_path: Path):
    """Generate a report of the migrated data."""
    cursor = conn.cursor()

    report = []
    report.append("=" * 80)
    report.append("DATABASE MIGRATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Overall stats
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comments")
    total_comments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT subreddit) FROM posts")
    total_subreddits = cursor.fetchone()[0]

    report.append("OVERALL STATISTICS")
    report.append("-" * 80)
    report.append(f"Total subreddits: {total_subreddits}")
    report.append(f"Total posts: {total_posts}")
    report.append(f"Total comments: {total_comments}")
    report.append(f"Average comments per post: {total_comments/total_posts:.1f}")
    report.append("")

    # Top subreddits by post count
    report.append("TOP 20 SUBREDDITS BY POST COUNT")
    report.append("-" * 80)
    report.append(f"{'Subreddit':<30} {'Posts':<10} {'Avg Score':<12} {'Comments'}")
    report.append("-" * 80)

    cursor.execute("""
        SELECT subreddit, total_posts, avg_post_score, total_comments
        FROM subreddit_stats
        ORDER BY total_posts DESC
        LIMIT 20
    """)

    for row in cursor.fetchall():
        report.append(f"{row[0]:<30} {row[1]:<10} {row[2]:<12.1f} {row[3]}")

    report.append("")

    # Top posts by score
    report.append("TOP 20 POSTS BY SCORE")
    report.append("-" * 80)
    report.append(f"{'Score':<8} {'Subreddit':<20} Title")
    report.append("-" * 80)

    cursor.execute("""
        SELECT score, subreddit, title
        FROM posts
        ORDER BY score DESC
        LIMIT 20
    """)

    for row in cursor.fetchall():
        title = row[2][:50] + "..." if len(row[2]) > 50 else row[2]
        report.append(f"{row[0]:<8} {row[1]:<20} {title}")

    report.append("")
    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")


def verify_migration(conn: sqlite3.Connection, original_data: Dict):
    """Verify that migration was successful."""
    print("\nVerifying migration...")

    cursor = conn.cursor()

    # Count original posts
    original_posts = sum(len(posts) for posts in original_data.values())
    original_comments = sum(
        len(post.get('comments', []))
        for posts in original_data.values()
        for post in posts
    )

    # Count migrated posts
    cursor.execute("SELECT COUNT(*) FROM posts")
    migrated_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comments")
    migrated_comments = cursor.fetchone()[0]

    # Verify
    print(f"Original posts: {original_posts}")
    print(f"Migrated posts: {migrated_posts}")
    print(f"Original comments: {original_comments}")
    print(f"Migrated comments: {migrated_comments}")

    if migrated_posts == original_posts and migrated_comments == original_comments:
        print("✓ Migration verified successfully!")
        return True
    else:
        print("✗ Migration verification failed!")
        print(f"  Missing posts: {original_posts - migrated_posts}")
        print(f"  Missing comments: {original_comments - migrated_comments}")
        return False


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent

    # Paths
    json_path = base_dir / "data" / "reddit_fashion_data.json"
    db_path = base_dir / "data" / "fashion.db"
    report_path = base_dir / "reports" / "migration_report.txt"

    # Create reports directory
    report_path.parent.mkdir(exist_ok=True)

    # Check if JSON exists
    if not json_path.exists():
        print(f"Error: JSON file not found at {json_path}", file=sys.stderr)
        sys.exit(1)

    # Warn if database already exists
    if db_path.exists():
        response = input(f"Database already exists at {db_path}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)
        db_path.unlink()

    print(f"Loading JSON data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} subreddits")
    total_posts = sum(len(posts) for posts in data.values())
    print(f"Total posts to migrate: {total_posts}")

    # Create database
    print(f"\nCreating database at {db_path}...")
    conn = sqlite3.connect(db_path)

    try:
        create_database_schema(conn)
        migrate_data(conn, data)
        verify_migration(conn, data)
        generate_migration_report(conn, report_path)

        # Get database size
        db_size_mb = db_path.stat().st_size / (1024 * 1024)
        json_size_mb = json_path.stat().st_size / (1024 * 1024)

        print(f"\nFile sizes:")
        print(f"  Original JSON: {json_size_mb:.1f} MB")
        print(f"  SQLite DB: {db_size_mb:.1f} MB")
        print(f"  Space saved: {json_size_mb - db_size_mb:.1f} MB ({(1 - db_size_mb/json_size_mb)*100:.1f}%)")

        print(f"\n✓ Migration complete! Database saved to: {db_path}")

    except Exception as e:
        print(f"\nError during migration: {e}", file=sys.stderr)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
