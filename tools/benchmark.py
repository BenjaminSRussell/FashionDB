#!/usr/bin/env python3
"""
Benchmarking Tool for FashionDB
Tests and compares different scraping strategies.
"""

import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class Benchmark:
    """Base benchmark class."""

    def __init__(self, name: str):
        self.name = name
        self.results = {}

    def run(self):
        """Override in subclass."""
        raise NotImplementedError

    def report(self):
        """Print benchmark results."""
        print(f"\n{'=' * 60}")
        print(f"BENCHMARK: {self.name}")
        print(f"{'=' * 60}")
        for key, value in self.results.items():
            print(f"{key}: {value}")
        print(f"{'=' * 60}\n")


class JSONPerformanceBenchmark(Benchmark):
    """Test JSON file operations performance."""

    def __init__(self, json_path: Path):
        super().__init__("JSON Performance")
        self.json_path = json_path

    def run(self):
        """Run JSON performance tests."""
        print(f"Testing JSON performance with {self.json_path}...")

        # Test 1: Load time
        start = time.time()
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        load_time = time.time() - start
        self.results['Load time (s)'] = f"{load_time:.2f}"

        # Test 2: Query time (find posts by subreddit)
        start = time.time()
        target_sub = list(data.keys())[0] if data else None
        if target_sub:
            posts = data[target_sub]
        query_time = time.time() - start
        self.results['Query time (s)'] = f"{query_time:.4f}"

        # Test 3: Filter time (find high-score posts)
        start = time.time()
        high_score_posts = [
            post for posts in data.values()
            for post in posts
            if post.get('score', 0) > 100
        ]
        filter_time = time.time() - start
        self.results['Filter time (s)'] = f"{filter_time:.2f}"
        self.results['High score posts found'] = len(high_score_posts)

        # Memory stats
        total_posts = sum(len(posts) for posts in data.values())
        self.results['Total posts'] = total_posts
        self.results['File size (MB)'] = f"{self.json_path.stat().st_size / (1024*1024):.1f}"


class SQLitePerformanceBenchmark(Benchmark):
    """Test SQLite database operations performance."""

    def __init__(self, db_path: Path):
        super().__init__("SQLite Performance")
        self.db_path = db_path

    def run(self):
        """Run SQLite performance tests."""
        if not self.db_path.exists():
            print(f"Database not found at {self.db_path}")
            self.results['Status'] = 'Database not created yet'
            return

        print(f"Testing SQLite performance with {self.db_path}...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Test 1: Connection time
        start = time.time()
        conn2 = sqlite3.connect(self.db_path)
        conn2.close()
        connect_time = time.time() - start
        self.results['Connect time (s)'] = f"{connect_time:.4f}"

        # Test 2: Query time (find posts by subreddit)
        start = time.time()
        cursor.execute("SELECT * FROM posts WHERE subreddit = 'malefashionadvice'")
        posts = cursor.fetchall()
        query_time = time.time() - start
        self.results['Query time (s)'] = f"{query_time:.4f}"

        # Test 3: Filter time (find high-score posts)
        start = time.time()
        cursor.execute("SELECT * FROM posts WHERE score > 100")
        high_score_posts = cursor.fetchall()
        filter_time = time.time() - start
        self.results['Filter time (s)'] = f"{filter_time:.4f}"
        self.results['High score posts found'] = len(high_score_posts)

        # Stats
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        self.results['Total posts'] = total_posts
        self.results['File size (MB)'] = f"{self.db_path.stat().st_size / (1024*1024):.1f}"

        conn.close()


class QueryEffectivenessBenchmark(Benchmark):
    """Benchmark query effectiveness."""

    def __init__(self, data_path: Path, queries_path: Path):
        super().__init__("Query Effectiveness")
        self.data_path = data_path
        self.queries_path = queries_path

    def run(self):
        """Run query effectiveness tests."""
        print("Testing query effectiveness...")

        # Load data
        with open(self.data_path, 'r') as f:
            data = json.load(f)

        with open(self.queries_path, 'r') as f:
            queries = json.load(f)

        # Sample analysis (simplified)
        total_queries = sum(len(q_list) for q_list in queries.values())
        sample_size = 100  # Test first 100 queries

        matched_queries = 0
        sample_count = 0

        for category, query_list in queries.items():
            for query in query_list[:10]:  # Sample 10 from each category
                if sample_count >= sample_size:
                    break

                # Simple matching
                query_terms = set(query.lower().split())
                found = False

                for posts in data.values():
                    for post in posts:
                        title = post.get('title', '').lower()
                        if any(term in title for term in query_terms):
                            found = True
                            break
                    if found:
                        break

                if found:
                    matched_queries += 1
                sample_count += 1

        match_rate = (matched_queries / sample_count) * 100 if sample_count > 0 else 0

        self.results['Total queries'] = total_queries
        self.results['Sample size'] = sample_count
        self.results['Queries with matches'] = matched_queries
        self.results['Match rate (%)'] = f"{match_rate:.1f}"
        self.results['Estimated low-value queries'] = int(total_queries * (1 - match_rate/100))


class DataQualityBenchmark(Benchmark):
    """Benchmark data quality metrics."""

    def __init__(self, data_path: Path):
        super().__init__("Data Quality")
        self.data_path = data_path

    def run(self):
        """Run data quality tests."""
        print("Testing data quality...")

        with open(self.data_path, 'r') as f:
            data = json.load(f)

        total_posts = 0
        total_comments = 0
        high_score_posts = 0
        posts_with_comments = 0
        empty_selftexts = 0

        for posts in data.values():
            for post in posts:
                total_posts += 1

                score = post.get('score', 0)
                if score > 50:
                    high_score_posts += 1

                comments = post.get('comments', [])
                total_comments += len(comments)
                if comments:
                    posts_with_comments += 1

                if not post.get('selftext', '').strip():
                    empty_selftexts += 1

        self.results['Total posts'] = total_posts
        self.results['Total comments'] = total_comments
        self.results['Avg comments/post'] = f"{total_comments/total_posts:.1f}" if total_posts > 0 else "0"
        self.results['High score posts (>50)'] = high_score_posts
        self.results['High score rate (%)'] = f"{high_score_posts/total_posts*100:.1f}" if total_posts > 0 else "0"
        self.results['Posts with comments (%)'] = f"{posts_with_comments/total_posts*100:.1f}" if total_posts > 0 else "0"
        self.results['Empty selftexts (%)'] = f"{empty_selftexts/total_posts*100:.1f}" if total_posts > 0 else "0"


def run_all_benchmarks(base_dir: Path):
    """Run all benchmarks and generate report."""
    json_path = base_dir / "data" / "reddit_fashion_data.json"
    db_path = base_dir / "data" / "fashion.db"
    queries_path = base_dir / "RedditDB" / "search_queries.json"
    report_path = base_dir / "reports" / "benchmark_report.txt"

    # Create reports directory
    report_path.parent.mkdir(exist_ok=True)

    print("=" * 60)
    print("FASHIONDB BENCHMARKING SUITE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Run benchmarks
    benchmarks = []

    if json_path.exists():
        b = DataQualityBenchmark(json_path)
        b.run()
        b.report()
        benchmarks.append(b)

        b = JSONPerformanceBenchmark(json_path)
        b.run()
        b.report()
        benchmarks.append(b)

    if db_path.exists():
        b = SQLitePerformanceBenchmark(db_path)
        b.run()
        b.report()
        benchmarks.append(b)

    if json_path.exists() and queries_path.exists():
        b = QueryEffectivenessBenchmark(json_path, queries_path)
        b.run()
        b.report()
        benchmarks.append(b)

    # Generate comparison report
    if json_path.exists() and db_path.exists():
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON: JSON vs SQLite")
        print("=" * 60)
        json_bench = next((b for b in benchmarks if isinstance(b, JSONPerformanceBenchmark)), None)
        sqlite_bench = next((b for b in benchmarks if isinstance(b, SQLitePerformanceBenchmark)), None)

        if json_bench and sqlite_bench:
            print(f"{'Metric':<30} {'JSON':<15} {'SQLite':<15} {'Improvement'}")
            print("-" * 70)

            # Compare query time
            json_query = float(json_bench.results.get('Query time (s)', '0'))
            sqlite_query = float(sqlite_bench.results.get('Query time (s)', '0'))
            if json_query > 0 and sqlite_query > 0:
                improvement = f"{json_query/sqlite_query:.1f}x faster"
                print(f"{'Query time':<30} {json_query:<15.4f} {sqlite_query:<15.4f} {improvement}")

            # Compare filter time
            json_filter = float(json_bench.results.get('Filter time (s)', '0'))
            sqlite_filter = float(sqlite_bench.results.get('Filter time (s)', '0'))
            if json_filter > 0 and sqlite_filter > 0:
                improvement = f"{json_filter/sqlite_filter:.1f}x faster"
                print(f"{'Filter time':<30} {json_filter:<15.4f} {sqlite_filter:<15.4f} {improvement}")

        print("=" * 60)

    # Save report
    with open(report_path, 'w') as f:
        f.write(f"FashionDB Benchmark Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for benchmark in benchmarks:
            f.write(f"{benchmark.name}\n")
            f.write("-" * 60 + "\n")
            for key, value in benchmark.results.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")

    print(f"\nBenchmark report saved to: {report_path}")


def main():
    """Main execution."""
    base_dir = Path(__file__).parent.parent
    run_all_benchmarks(base_dir)


if __name__ == "__main__":
    main()
