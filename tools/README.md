# FashionDB Tools

Utility scripts for analyzing, optimizing, and improving the FashionDB scraping system.

## Tools Overview

### 1. `analyze_queries.py` - Query Effectiveness Analyzer

Analyzes which search queries are most effective for finding fashion rules.

**Usage:**
```bash
python3 tools/analyze_queries.py
```

**Output:**
- `reports/query_effectiveness.txt` - Human-readable report
- `reports/query_effectiveness.json` - Detailed JSON results

**What it does:**
- Tests all 1,588 queries against existing data
- Ranks queries by matches found, engagement, and quality
- Identifies top 50 and bottom 50 performers
- Shows category-level statistics
- Recommends queries to keep/remove

**Use this to:**
- Understand which queries are actually working
- Remove low-performing queries
- Focus scraping effort on high-yield queries

---

### 2. `optimize_queries.py` - Query Optimizer

Generates an optimized set of ~300 high-impact queries from the original 1,588.

**Usage:**
```bash
python3 tools/optimize_queries.py
```

**Output:**
- `RedditDB/search_queries_optimized.json` - Optimized query set
- `reports/query_optimization.txt` - Optimization report

**What it does:**
- Deduplicates similar queries
- Extracts core fundamental queries
- Generates scenario-based queries
- Creates advanced Reddit search queries with operators
- Reduces 1,588 queries → ~300 high-impact queries

**Use this to:**
- Get a curated set of effective queries
- Reduce API calls and rate limit issues
- Improve scraping efficiency

---

### 3. `migrate_to_sqlite.py` - Database Migration Tool

Migrates data from JSON to SQLite database for better performance and scalability.

**Usage:**
```bash
python3 tools/migrate_to_sqlite.py
```

**Output:**
- `data/fashion.db` - SQLite database
- `reports/migration_report.txt` - Migration summary

**What it does:**
- Creates optimized database schema
- Migrates all posts and comments
- Creates indexes for fast querying
- Generates subreddit statistics
- Verifies data integrity

**Database Schema:**
- `posts` - All Reddit posts
- `comments` - All comments
- `query_metrics` - Query performance tracking
- `subreddit_stats` - Subreddit metadata

**Benefits:**
- 10-1000x faster queries
- Scales to millions of rows
- Enables complex analytics
- More space-efficient
- ACID compliance

---

### 4. `benchmark.py` - Performance Benchmarking Tool

Tests and compares different strategies (JSON vs SQLite, query effectiveness, data quality).

**Usage:**
```bash
python3 tools/benchmark.py
```

**Output:**
- `reports/benchmark_report.txt` - Benchmark results

**What it benchmarks:**
- **JSON Performance:** Load time, query time, filter time
- **SQLite Performance:** Connect time, query time, filter time
- **Query Effectiveness:** Match rate, low-value query detection
- **Data Quality:** Posts, comments, scores, coverage

**Use this to:**
- Measure improvements objectively
- Compare JSON vs SQLite performance
- Validate optimization efforts
- Track progress toward 1M rules

---

## Quick Start Guide

### Step 1: Analyze Current State

```bash
# See what queries are working
python3 tools/analyze_queries.py

# Check current performance
python3 tools/benchmark.py
```

Review the reports in `reports/` directory.

### Step 2: Optimize Queries

```bash
# Generate optimized query set
python3 tools/optimize_queries.py
```

Review `RedditDB/search_queries_optimized.json` and decide if you want to use it.

### Step 3: Migrate to Database (Recommended)

```bash
# Migrate to SQLite
python3 tools/migrate_to_sqlite.py
```

This creates `data/fashion.db` which you can query with SQL.

### Step 4: Re-benchmark

```bash
# Compare performance
python3 tools/benchmark.py
```

Should show significant performance improvements.

---

## Requirements

```bash
# Standard library only - no additional dependencies needed!
# (Except for the main scraper which needs praw, prawcore, etc.)
```

---

## Directory Structure

```
FashionDB/
├── tools/                      # These utility scripts
│   ├── analyze_queries.py
│   ├── optimize_queries.py
│   ├── migrate_to_sqlite.py
│   ├── benchmark.py
│   └── README.md              # This file
├── reports/                    # Generated reports
│   ├── query_effectiveness.txt
│   ├── query_optimization.txt
│   ├── migration_report.txt
│   └── benchmark_report.txt
├── data/
│   ├── reddit_fashion_data.json   # Original data
│   └── fashion.db              # SQLite database (after migration)
└── RedditDB/
    ├── search_queries.json     # Original 1,588 queries
    └── search_queries_optimized.json  # Optimized ~300 queries
```

---

## Common Workflows

### Workflow 1: Quick Analysis

```bash
# Just want to see what's working?
python3 tools/analyze_queries.py
python3 tools/benchmark.py
```

### Workflow 2: Optimize Queries Only

```bash
# Want better queries but keep JSON?
python3 tools/optimize_queries.py

# Then update your scraper to use:
# RedditDB/search_queries_optimized.json
```

### Workflow 3: Full Migration

```bash
# Ready for production scalability?
python3 tools/analyze_queries.py    # Understand current state
python3 tools/optimize_queries.py   # Get better queries
python3 tools/migrate_to_sqlite.py  # Migrate to database
python3 tools/benchmark.py          # Verify improvements
```

---

## Advanced Usage

### Using the SQLite Database

After migration, you can query the database directly:

```bash
sqlite3 data/fashion.db
```

Example queries:
```sql
-- Top subreddits by post count
SELECT subreddit, total_posts, avg_post_score
FROM subreddit_stats
ORDER BY total_posts DESC
LIMIT 20;

-- High-scoring posts
SELECT title, score, subreddit
FROM posts
WHERE score > 100
ORDER BY score DESC
LIMIT 50;

-- Posts about fit
SELECT title, score, url
FROM posts
WHERE title LIKE '%fit%'
ORDER BY score DESC;

-- Comments on a specific post
SELECT body, score
FROM comments
WHERE post_id = 'abc123'
ORDER BY score DESC;
```

### Integrating with Scraper

To use optimized queries in your scraper:

```python
# In scrape_malefashion.py, change:
SEARCH_QUERIES_PATH: Path = BASE_DIR / "search_queries_optimized.json"
```

To use SQLite for output:

```python
# Replace write_scrape_data() with database inserts
import sqlite3
conn = sqlite3.connect('data/fashion.db')
cursor = conn.cursor()
cursor.execute("INSERT INTO posts (...) VALUES (...)")
conn.commit()
```

---

## Troubleshooting

### "File not found" errors
Make sure you're running from the FashionDB root directory:
```bash
cd /path/to/FashionDB
python3 tools/analyze_queries.py
```

### Database already exists
The migration script will ask before overwriting. To force:
```bash
rm data/fashion.db
python3 tools/migrate_to_sqlite.py
```

### Memory errors with large JSON
The JSON is 82MB. If you have memory issues:
- Close other applications
- Use a machine with at least 4GB RAM
- Or migrate to SQLite which handles large data better

---

## Next Steps

After running these tools, see `ANALYSIS_AND_STRATEGY.md` for:
- Detailed improvement recommendations
- Subreddit expansion strategy
- Multi-source scraping architecture
- Path to 1 million rules

---

## Questions?

Refer to `ANALYSIS_AND_STRATEGY.md` for comprehensive analysis and strategy.
