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

## Troubleshooting

Reddit API: Check credentials in `config/config.ini`
Import errors: `pip install -r requirements.txt`
Empty results: Verify URLs and check logs
Data not saving: Check directory permissions
