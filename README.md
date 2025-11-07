# FashionDB

**A comprehensive database of menswear fashion rules extracted from Reddit and other fashion communities.**

## 🎯 Project Goal

Build a database of **1 million fashion rules** by scraping and analyzing discussions from Reddit, fashion forums, blogs, and other sources.

## 📊 Current Status

- **Posts collected:** 27,341
- **Subreddits:** 38
- **Data size:** 82MB
- **Search queries:** 1,588 (optimizable to ~300)
- **Status:** Foundation complete, ready for scaling

## 🚀 Quick Start

### Run Complete Analysis

```bash
./run_analysis.sh
```

This will:
1. Analyze query effectiveness
2. Run performance benchmarks
3. Generate optimized query set
4. Create summary report

All reports will be in `reports/` directory.

### Migrate to Database (Recommended)

```bash
python3 tools/migrate_to_sqlite.py
```

Converts 82MB JSON → optimized SQLite database with 10-1000x faster queries.

## 📁 Project Structure

```
FashionDB/
├── RedditDB/
│   ├── scrape_malefashion.py       # Main Reddit scraper
│   ├── search_queries.json         # 1,588 search queries
│   ├── search_queries_optimized.json  # Optimized ~300 queries
│   └── target_subreddits.json      # Target subreddit list
│
├── standardization/
│   ├── ollama.py                   # Rule extraction with Ollama
│   └── schema.json                 # Rule schema definition
│
├── data/
│   ├── reddit_fashion_data.json    # Scraped Reddit data (82MB)
│   └── fashion.db                  # SQLite database (after migration)
│
├── tools/
│   ├── analyze_queries.py          # Query effectiveness analyzer
│   ├── optimize_queries.py         # Query optimizer
│   ├── migrate_to_sqlite.py        # Database migration tool
│   ├── benchmark.py                # Performance benchmarking
│   └── README.md                   # Tool documentation
│
├── reports/                        # Generated analysis reports
│
├── ANALYSIS_AND_STRATEGY.md        # Detailed strategic analysis
├── IMPLEMENTATION_ROADMAP.md       # Step-by-step implementation guide
└── run_analysis.sh                 # Master analysis script
```

## 🔧 Tools

### Analysis Tools

| Tool | Purpose | Output |
|------|---------|--------|
| `analyze_queries.py` | Find which queries work best | `reports/query_effectiveness.txt` |
| `optimize_queries.py` | Generate optimized query set | `RedditDB/search_queries_optimized.json` |
| `benchmark.py` | Measure performance | `reports/benchmark_report.txt` |
| `migrate_to_sqlite.py` | Convert JSON → SQLite | `data/fashion.db` |

See [`tools/README.md`](tools/README.md) for detailed usage.

## 📈 Scaling Strategy

### Current: 27K Posts
- 38 subreddits
- JSON storage
- 1,588 queries

### Target: 1M Rules

**Phase 1:** Foundation ✅
- Analysis tools built
- Database migration ready
- Query optimization complete

**Phase 2:** Optimization (Week 2-3)
- Migrate to SQLite
- Reduce queries to 300
- Add 50 new subreddits
- Target: 100K posts

**Phase 3:** Multi-Source (Week 4-5)
- Add StyleForum scraper
- Add blog scrapers
- Add YouTube transcripts
- Target: 300K posts

**Phase 4:** Rule Extraction (Week 6-7)
- Process all posts with Ollama
- Extract and standardize rules
- Deduplicate and score
- Target: 500K rules

**Phase 5:** Scale to 1M (Week 8-12)
- 100 subreddits → 500K rules
- Forums → 200K rules
- Blogs/YouTube → 300K rules
- **Total: 1M+ rules**

See [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) for details.

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [`ANALYSIS_AND_STRATEGY.md`](ANALYSIS_AND_STRATEGY.md) | Comprehensive analysis of current approach, problems identified, and strategic recommendations |
| [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) | Week-by-week implementation plan to reach 1M rules |
| [`tools/README.md`](tools/README.md) | Detailed guide for all analysis and optimization tools |

## 🎯 Key Improvements Identified

### 1. Data Storage ⚠️
**Problem:** 82MB JSON file hitting limits
**Solution:** Migrate to SQLite (10-1000x faster)

### 2. Query Strategy ⚠️
**Problem:** 1,588 queries, many ineffective
**Solution:** Optimize to ~300 high-impact queries

### 3. Scalability 🚨
**Problem:** Single Reddit source can't reach 1M
**Solution:** Multi-source architecture (forums, blogs, YouTube)

### 4. Testing ⚠️
**Problem:** No way to measure improvements
**Solution:** Comprehensive benchmarking framework

## 🔬 Analysis Results

Run the analysis to see:
- Which queries are most effective
- Current vs potential performance
- Recommended optimizations
- Path to 1M rules

```bash
./run_analysis.sh
```

## 🛠️ Requirements

### Python Dependencies
```bash
# For scraping
pip install praw prawcore

# For rule extraction
pip install ollama pydantic

# Standard library (no install needed):
# - json, sqlite3, pathlib, argparse
```

### Reddit API
You need Reddit API credentials in `config/config.ini`:
```ini
[DEFAULT]
client_id = your_client_id
client_secret = your_client_secret
username = your_username
password = your_password
user_agent = your_user_agent
```

## 🚦 Next Steps

### Option A: Full Rebuild (Recommended)
Best for scaling to 1M rules.

```bash
# 1. Run analysis
./run_analysis.sh

# 2. Migrate to database
python3 tools/migrate_to_sqlite.py

# 3. Update scraper to use:
#    - SQLite database
#    - Optimized queries

# 4. Expand and scrape
#    - Add new subreddits
#    - Implement multi-source
```

### Option B: Incremental Improvement
Start with quick wins, migrate later.

```bash
# 1. Use optimized queries
#    Update scraper config

# 2. Add new subreddits
#    Edit target_subreddits.json

# 3. Continue scraping
python3 RedditDB/scrape_malefashion.py

# 4. Migrate when needed
```

### Option C: Continue As-Is
Keep current architecture, focus on expansion only.

## 📊 Success Metrics

Track progress with benchmarks:
```bash
python3 tools/benchmark.py
```

**Target metrics:**
- Query match rate: >80%
- Rule extraction success: >70%
- Avg rule confidence: >0.65
- Database query time: <0.01s
- Total rules: 1M+

## 🤝 Contributing

This is a personal project, but suggestions welcome via issues.

## 📝 License

Not specified - personal research project.

## ❓ FAQ

### Q: Why SQLite instead of PostgreSQL/MongoDB?
A: SQLite is sufficient for <2M rules, requires no server, and is portable. Can migrate later if needed.

### Q: How long to reach 1M rules?
A: Estimated 8-15 weeks with full implementation (see roadmap).

### Q: What about data quality?
A: Rules have confidence scores. Can filter for >0.65 confidence for high-quality subset.

### Q: Can I use this data?
A: Check original content licenses. Reddit data subject to Reddit ToS.

## 🔗 Resources

- [Reddit API Documentation](https://www.reddit.com/dev/api/)
- [PRAW Documentation](https://praw.readthedocs.io/)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

---

**Ready to scale to 1M rules?** Start with `./run_analysis.sh` and review the reports!
