# FashionDB

A comprehensive fashion data collection and analysis system that scrapes, processes, and extracts fashion rules from Reddit and web sources.

## Project Structure

```
FashionDB/
├── Beans/              # Web scraping for fashion rules from websites
├── RedditDB/           # Reddit data collection from fashion subreddits
├── Data Analysis/      # ML/NLP pipeline for analyzing fashion data
├── config/             # Configuration files (gitignored)
├── data/               # Processed data files (gitignored)
└── requirements.txt    # Python dependencies
```

## Components

### 1. RedditDB
Scrapes fashion-related posts and comments from Reddit using the PRAW API.

**Features:**
- Configurable subreddit targets
- Custom search queries
- Score-based filtering
- Automatic saving and crash recovery

### 2. Beans
Web scraper that extracts fashion rules from web pages.

**Features:**
- Pattern-based rule extraction
- Deduplication and merging
- Quality scoring and validation
- Multi-threaded scraping

### 3. Data Analysis
NLP and ML pipeline for processing scraped data.

**Features:**
- Fashion rule extraction using LLMs
- Semantic analysis and clustering
- Duplicate detection
- Text standardization and spell checking

## Installation

### Prerequisites
- Python 3.8+
- Reddit API credentials (for RedditDB)
- Ollama (optional, for LLM-based extraction)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd FashionDB
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Reddit API (for RedditDB):**
   - Copy the example config: `cp config/config.ini.example config/config.ini`
   - Get Reddit API credentials from https://www.reddit.com/prefs/apps
   - Edit `config/config.ini` with your credentials

4. **Configure Reddit targets (for RedditDB):**
   ```bash
   cp RedditDB/target_subreddits.json.example RedditDB/target_subreddits.json
   cp RedditDB/search_queries.json.example RedditDB/search_queries.json
   ```
   Edit these files to customize which subreddits and queries to use.

5. **Configure Beans (optional):**
   ```bash
   cp config/extraction_rules.json.example config/extraction_rules.json
   ```

## Usage

### RedditDB: Scrape Reddit Data

```bash
cd RedditDB
python scrape_malefashion.py
```

The scraper will:
- Search configured subreddits for fashion-related posts
- Save posts and high-quality comments
- Auto-save progress periodically
- Gracefully handle Ctrl+C interrupts

Output: `data/reddit_fashion_data.json`

### Beans: Extract Fashion Rules from URLs

1. **Create a URLs file** (one URL per line):
   ```
   https://www.example.com/fashion-guide
   https://www.example.com/style-tips
   ```

2. **Run the full pipeline:**
   ```bash
   cd Beans
   python run.py full urls.txt
   ```

   Or run individual steps:
   ```bash
   # Scrape URLs
   python run.py scrape urls.txt data/raw_rules.json

   # Deduplicate and merge
   python run.py distill data data/rules_raw.json

   # Filter invalid rules
   python run.py filter data/rules_raw.json data/rules.json

   # Validate final rules
   python run.py validate data/rules.json
   ```

Output: `Beans/data/rules.json`

### Data Analysis: Process Scraped Data

The Data Analysis component provides several scripts for processing the scraped data:

```bash
cd "Data Analysis"

# Extract fashion rules from Reddit data
python test_extraction.py

# Perform semantic separation
python src/semantic_separation.py

# Remove duplicates
python src/duplicates.py

# Spell check and standardization
python src/standardization/ollama.py
```

## Configuration

### Reddit API (`config/config.ini`)
```ini
[DEFAULT]
client_id = YOUR_CLIENT_ID
client_secret = YOUR_CLIENT_SECRET
username = YOUR_REDDIT_USERNAME
password = YOUR_REDDIT_PASSWORD
user_agent = FashionDB/1.0 by YOUR_USERNAME
```

### Target Subreddits (`RedditDB/target_subreddits.json`)
```json
[
  "malefashionadvice",
  "frugalmalefashion",
  "femalefashionadvice"
]
```

### Search Queries (`RedditDB/search_queries.json`)
```json
{
  "basic_advice": ["how to wear", "guide", "basics"],
  "style_rules": ["rule", "always", "never"]
}
```

## Data Output Format

### Reddit Data Format
```json
{
  "subreddit_name": [
    {
      "post_id": "abc123",
      "title": "Post title",
      "score": 150,
      "url": "https://reddit.com/...",
      "flair": "Discussion",
      "selftext": "Post content...",
      "comments": [
        {
          "comment_id": "def456",
          "body": "Comment text...",
          "score": 50
        }
      ]
    }
  ]
}
```

### Fashion Rules Format (Beans)
```json
{
  "rules": [
    {
      "rule_text": "Always match your belt with your shoes.",
      "rule_type": "color_matching",
      "word_count": 7,
      "quality_score": 0.85,
      "sources": [
        {
          "url": "https://example.com/guide",
          "domain": "example.com"
        }
      ],
      "source_count": 1
    }
  ],
  "statistics": {
    "total_rules": 150,
    "unique_domains": 10,
    "avg_quality_score": 0.72
  }
}
```

## Development

### Running Tests
```bash
# Test MLX LLM integration (macOS only)
cd "Data Analysis"
python test_mlx.py

# Test fashion rule extraction
python test_extraction.py
```

### Project Status

This project is in active development. Current state:
- ✅ Reddit scraping functional
- ✅ Web scraping and rule extraction working
- ✅ Basic validation and deduplication
- ⚠️  Data analysis pipeline partially implemented
- ⚠️  LLM integration optional (Ollama)

## Troubleshooting

### Reddit API Issues
- Ensure your `config/config.ini` has valid credentials
- Check that your Reddit app has the correct permissions
- Rate limiting: The scraper respects Reddit's API limits

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Some dependencies are optional (e.g., mlx-lm for macOS)

### Empty Results
- Check that your URLs file is formatted correctly (one URL per line)
- Verify that target websites are accessible
- Review logs for specific error messages

### Data Not Saving
- Ensure the `data/` directories exist and are writable
- Check disk space
- Look for `emergency_save_*.json` files if crashes occurred

## License

See [LICENSE](LICENSE) file for details.

## Contributing

This is an active research/development project. Contributions, suggestions, and bug reports are welcome.

## Notes

- All configuration files in `config/` are gitignored for security
- Data files are gitignored to avoid large commits
- Example configuration files are provided with `.example` suffix
- The system is designed to be robust to interruptions and network failures
