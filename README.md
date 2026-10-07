# FashionDB

Fashion data collection and analysis system. Scrapes Reddit and web sources for fashion rules.

## Structure

```
FashionDB/
├── Beans/              # Web scraping for fashion rules
├── RedditDB/           # Reddit data collection
├── Data Analysis/      # NLP processing pipeline
├── config/             # Configuration files
├── data/               # Processed data
└── requirements.txt
```

## Installation

Prerequisites: Python 3.8+, Reddit API credentials
- Ollama (optional, for LLM-based extraction)

Setup:

```bash
pip install -r requirements.txt

# Configure Reddit API
cp config/config.ini.example config/config.ini
# Edit config.ini with credentials from https://www.reddit.com/prefs/apps

# Configure targets
cp RedditDB/target_subreddits.json.example RedditDB/target_subreddits.json
cp RedditDB/search_queries.json.example RedditDB/search_queries.json
cp config/extraction_rules.json.example config/extraction_rules.json
```

## Usage

RedditDB:
```bash
cd RedditDB
python scrape_malefashion.py
```

Beans:
```bash
cd Beans
python run.py full urls.txt
```

Data Analysis:
```bash
cd "Data Analysis"
python test_extraction.py
python src/semantic_separation.py
python src/duplicates.py
```

## Output

Reddit data: `data/reddit_fashion_data.json`
Beans rules: `Beans/data/rules.json`

## Beans clean thresholds

`python run.py full …` uses the same defaults as `clean.py` CLI:
- min words: 5
- max words: 50
- min quality score: 7

Do not tighten `max_word_count` below ~20 — natural-language fashion advice is longer than 7 words.

## Troubleshooting

Reddit API: Check credentials in `config/config.ini`
Import errors: `pip install -r requirements.txt`
Empty results: Verify URLs and check logs
Data not saving: Check directory permissions

## Beans pipeline

One-command rule extraction (discover/scrape → distill → clean → filter → validate):

```bash
make -C Beans pipeline URLS=test_urls.txt
# offline fixture path (no network):
make -C Beans pipeline-offline
```

`python Beans/run.py full <urls_or_domain>` writes `Beans/data/run_manifest.json` with stage timings and exits non-zero when validation finds invalid rules.


## fashiondb CLI

```bash
python -m fashiondb check --wardrobe wardrobe.csv --rules rules.db --json-report report.json
python -m fashiondb export --rules rules.json --format parquet --out rules.parquet
```

Reddit scrape resume: checkpoints in `data/reddit_checkpoints.sqlite` (pass `--full` to ignore).


## Reddit OAuth bootstrap

Password auth is rejected. Use a **script** app + refresh token:

1. Create an app at https://www.reddit.com/prefs/apps (type: script).
2. Copy `client_id` / `client_secret` into `config/config.ini`.
3. Generate a refresh token once (e.g. [praw refresh token script](https://praw.readthedocs.io/en/stable/tutorials/refresh_token.html)) and set `refresh_token=...`.
4. Set a descriptive `user_agent` (not the placeholder).

`create_reddit_client()` fails fast if only `username`/`password` are present.
## Package layout (#4)

Import-safe packages (no spaces):

| Package | Former path |
|---------|-------------|
| `reddit_db/` | `RedditDB/` |
| `data_analysis/` | `Data Analysis/` |
| `beans/` | `Beans/` |
| `fashiondb/` | CLI + SQLite + embeddings + Gradio |

```bash
pip install -e ".[dev,ui]"
fashiondb check
fashiondb-reddit   # needs config/config.ini with refresh_token
```

## Reddit OAuth (#18)

`config/config.ini.example` uses **refresh_token** only (password grant rejected).
Create a script app at https://www.reddit.com/prefs/apps, obtain a refresh token once, paste into `config/config.ini`.

## Scrape → unique → extract (#16)

Canonical files live under repo-root `data/`:

- `data/reddit_fashion_data.json` — nested scrape output
- `data/reddit_fashion_data_unique.json` — flattened records (list)
- `data/fashion_rules_extracted.json` — extractor output

`fashion_rule_extractor.load_posts()` accepts both nested dict and unique list shapes.
Smoke: `python scripts/smoke_scrape_unique_extract.py`

## Embeddings + explorer (#7, #3)

```bash
fashiondb migrate-json
fashiondb embed-rules
fashiondb similar "white socks with a suit"
fashiondb explore   # Gradio UI (requires pip install -e ".[ui]")
```
>>>>>>> 3c3dc21 (feat: finish FashionDB — packages, OAuth, pipeline paths, embeddings, Gradio)
