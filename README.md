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


## fashiondb check CLI

CI-friendly wardrobe vs rules checker:

```bash
python -m fashiondb check --wardrobe path.csv --rules rules.jsonl --json
```

Exit code `0` when no violations, `1` when violations are found. Report schema: `fashiondb.check.report.v1` (`--schema` prints JSON Schema).
