# Fashion Content Scraping Guide

## Deterministic, Replicable Scraping System

This guide documents the deterministic scraping system for collecting high-quality fashion advice articles. All processes are designed to be **replicable** - running the same inputs will produce the same outputs.

## Current Status

**Database:** `data/independent_content.db`
- **169 articles** from **66 independent sources**
- **1.75 MB** of expert fashion content
- **1,740 words** average per article
- **31.4% complete** (no truncation)
- **17.8% high quality** (70+ quality score)

## System Architecture

### 1. Configuration (`tools/scraping_config.py`)

All scraping parameters are centralized and deterministic:

```python
SCRAPING_CONFIG = {
    'max_retries': 3,
    'retry_delay_seconds': 2.0,
    'request_delay_seconds': 1.0,
    'min_content_length': 300,
    # ... all settings in one place
}
```

**Key features:**
- Fixed delays (no randomness)
- Consistent retry behavior
- Deterministic headers and user agents
- Known good/bad sources listed

### 2. Scraping Process (`tools/scrape_web_search_urls.py`)

**Input:** JSON file with URLs
```json
{
  "topics": [
    {
      "topic": "Topic Name",
      "urls": ["url1", "url2", ...]
    }
  ]
}
```

**Process:**
1. Load URLs from JSON (deterministic order)
2. For each URL:
   - Make request with fixed delay
   - Retry up to 3 times with fixed 2s delay
   - Extract content using BeautifulSoup
   - Validate minimum length (300 chars)
   - Save to SQLite database
3. Generate comprehensive report

**Output:**
- Updated SQLite database
- JSON scraping report
- Text summary report

### 3. Quality Validation (`tools/validate_article_quality.py`)

**Deterministic quality metrics:**

```python
class ArticleQualityMetrics:
    word_count: int              # Exact word count
    fashion_term_count: int      # Count of fashion terms
    has_actionable_advice: bool  # Pattern matching
    truncated_likelihood: float  # 0-1 score
    quality_score: float         # 0-100 composite score
```

**Quality scoring formula:**
- Length (0-30 pts): word_count → points
- Structure (0-20 pts): paragraphs + lists
- Fashion content (0-30 pts): fashion term count
- Advice quality (0-10 pts): actionable patterns
- Style descriptions (0-10 pts): style patterns
- Truncation penalty: score × (1 - truncation × 0.5)

**All calculations are deterministic** - same article = same score every time.

## Running the System

### Step 1: Create URL Batch

Create JSON file with URLs to scrape:

```bash
# Example: data/batch_N_description.json
{
  "summary": {
    "total_urls": 20,
    "discovery_method": "site_specific_searches",
    "discovery_date": "2025-11-07",
    "focus": "topic description"
  },
  "topics": [
    {
      "topic": "Topic Name",
      "description": "Description",
      "urls": [
        "https://example.com/article1",
        "https://example.com/article2"
      ]
    }
  ]
}
```

### Step 2: Run Scraper

```bash
python3 tools/scrape_web_search_urls.py --input data/batch_N_description.json
```

**Deterministic behavior:**
- URLs processed in order
- Fixed 1s delay between requests
- 3 retries with 2s delays
- Same URL = same result

**Output:**
- Articles added to `data/independent_content.db`
- Report in `reports/web_search_scraping_report.txt`

### Step 3: Validate Quality

```bash
python3 tools/validate_article_quality.py
```

**Deterministic analysis:**
- Calculates quality metrics for ALL articles
- Exports metrics to `validation/article_quality_metrics.json`
- Exports 10 sample articles to `validation/samples/`
- All metrics are reproducible

**Output files:**
```
validation/
├── article_quality_metrics.json  # All article metrics
└── samples/
    ├── index.json               # Sample metadata
    ├── sample_01_<hash>.txt     # Full article text
    ├── sample_02_<hash>.txt
    └── ...
```

## Data Quality Guarantees

### Complete Articles

We validate article completeness through multiple checks:

1. **Length validation**: Minimum 300 characters
2. **Truncation detection**:
   - Check for incomplete sentences
   - Look for "read more" markers
   - Verify proper ending punctuation
3. **Structure validation**:
   - Paragraph count
   - Sentence count
   - Header presence

**Example: Complete Article**
```
Title: The Top 50 Best Style Tips for Men
Length: 64,155 characters (10,836 words)
Quality Score: 60/100
Truncation: 0.0 (complete)
Fashion Terms: 150+
Has Introduction: Yes
Has Conclusion: Yes
```

### Quality Scoring

Articles are scored 0-100 based on:

| Category | Points | Criteria |
|----------|--------|----------|
| Length | 0-30 | 1000+ words = 30 pts |
| Structure | 0-20 | Paragraphs + lists |
| Fashion Content | 0-30 | Fashion term density |
| Advice Quality | 0-10 | Actionable patterns |
| Style Descriptions | 0-10 | Style terminology |

**Quality tiers:**
- **High (70-100)**: 30 articles (17.8%)
- **Medium (40-69)**: 99 articles (58.6%)
- **Low (0-39)**: 40 articles (23.7%)

### Content Verification

Random samples exported for manual verification:

```bash
# View sample article
cat validation/samples/sample_01_*.txt

# Check sample index
cat validation/samples/index.json
```

Each sample includes:
- Full URL
- Source domain
- Complete article text
- Word count
- Scraped timestamp

## Success Rates by Strategy

### ✅ What Works (60-76% success)

1. **Specific article URLs** (not homepages)
   - Example: `site.com/guide-to-suits`
   - Success: 70.8%

2. **Independent blogs**
   - Put This On: 100%
   - Dappered: 100%
   - Stitchdown: 100%

3. **Mid-size publications**
   - He Spoke Style: 80%
   - Primer Magazine: 88.9%
   - Gentleman's Gazette: 55.6%

### ❌ What Fails (0-27% success)

1. **Homepage URLs**
   - Batch 4 homepages: 27.3%
   - Reason: Too generic, no content

2. **Luxury/commercial sites**
   - Mr Porter: 0% (Cloudflare)
   - The Armoury: 0% (JavaScript)
   - Hypebeast: 0% (405 errors)

3. **Sites with bot protection**
   - Listed in `BLOCKED_SOURCES`
   - Require browser automation

## Successful Batches

### Batch 5: Expert Articles (70.8% success)
- Permanent Style: 4/6 articles
- Ivy Style: 8/8 articles (100%!)
- Heddels: 5/10 articles

### Batch 6: Menswear Sources (65.1% success)
- Put This On: 8/8 articles (100%!)
- He Spoke Style: 8/10 articles (80%)
- Gentleman's Gazette: 5/9 articles

### Batch 7: Streetwear & Boots (76.1% success)
- Stitchdown: 9/9 articles (100%!)
- Dappered: 9/9 articles (100%!)
- Primer Magazine: 8/9 articles (88.9%)

## Reproducibility

### Deterministic Properties

✅ **Fixed configurations**: All delays, retries, thresholds in config
✅ **Ordered processing**: URLs processed in JSON order
✅ **Consistent extraction**: Same HTML → same output
✅ **Deterministic scoring**: Same content → same quality score
✅ **Seeded hashing**: Filenames use MD5 of URL (reproducible)

### Running Validation

To verify system reproducibility:

```bash
# Run validation twice
python3 tools/validate_article_quality.py > run1.txt
python3 tools/validate_article_quality.py > run2.txt

# Compare outputs (should be identical)
diff run1.txt run2.txt
```

No differences = perfect reproducibility

### Database Queries

Example queries for analysis:

```bash
# Check article statistics
python3 -c "
import sqlite3
conn = sqlite3.connect('data/independent_content.db')
cursor = conn.cursor()

# Count by source
cursor.execute('''
  SELECT source, COUNT(*), AVG(LENGTH(body))
  FROM scraped_content
  GROUP BY source
  ORDER BY COUNT(*) DESC
  LIMIT 10
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} articles, avg {int(row[2]):,} chars')
"
```

## Top Sources

Current top 10 sources by article count:

1. **Stitchdown** (10) - Boot & leather care
2. **Put This On** (10) - Shoes & tailoring
3. **Real Men Real Style** (10) - General style
4. **Ivy Style** (9) - Preppy/OCBD
5. **He Spoke Style** (9) - Suits & color
6. **Dappered** (9) - Affordable menswear
7. **Primer Magazine** (8) - Smart casual
8. **Highsnobiety** (7) - Streetwear
9. **Gentleman's Gazette** (7) - Dress codes
10. **Denimhunters** (6) - Denim expertise

## Content Coverage

### Topics Covered

✅ **Classic Menswear**
- Suits, tailoring, dress codes
- Formal wear, business attire
- Three-piece suits, double-breasted

✅ **Streetwear & Contemporary**
- Streetwear evolution
- Preppy-streetwear fusion
- 90s hip-hop fashion

✅ **Denim & Heritage**
- Raw selvedge denim
- Japanese denim
- Denim care & washing

✅ **Preppy & Ivy**
- OCBD guides
- Trad vs preppy vs ivy
- East Coast style

✅ **Minimalist & Affordable**
- Capsule wardrobes
- Budget style guides
- Lean wardrobe pyramid

✅ **Color & Coordination**
- Color theory
- Pattern mixing
- Style matching

✅ **Seasonal & Occasion**
- Date night outfits
- Fall/winter styling
- Business casual

✅ **Boots & Leather**
- Boot care
- Leather aging (patina)
- Shell cordovan care

## Next Steps

### Option 1: Continue Collection

Find more article URLs from accessible sources:
```bash
# Search for more articles
# Add to new batch JSON
# Run scraper
```

### Option 2: Improve Quality

Focus on high-quality sources (70%+ success rate):
- Put This On
- Dappered
- Stitchdown
- Ivy Style
- Primer Magazine

### Option 3: Analyze Content

Start extracting fashion rules from 169 articles:
```bash
# Future: Rule extraction pipeline
# Parse articles
# Extract advice patterns
# Build rule database
```

## Troubleshooting

### Issue: Low success rate

**Solution:** Check if URLs are from blocked sources
```python
from tools.scraping_config import is_blocked_source
if is_blocked_source(url):
    print("This source is blocked - skip it")
```

### Issue: Truncated articles

**Solution:** Check truncation scores in validation output
```bash
# Find truncated articles
python3 -c "
import json
with open('validation/article_quality_metrics.json') as f:
    data = json.load(f)
truncated = [a for a in data['articles'] if a['truncated_likelihood'] > 0.5]
print(f'Found {len(truncated)} truncated articles')
for a in truncated:
    print(f'  {a[\"url\"]}')
"
```

### Issue: Low quality scores

**Solution:** Prioritize sources with proven high quality:
- Longer articles (1000+ words)
- Specific guides (not listicles)
- Independent blogs (not commercial sites)

## Summary

This scraping system provides:

1. ✅ **Deterministic behavior** - reproducible results
2. ✅ **Quality validation** - comprehensive metrics
3. ✅ **Complete articles** - 53 verified complete (31.4%)
4. ✅ **Diverse sources** - 66 independent sites
5. ✅ **Rich content** - 169 articles, 1.75 MB, 1,740 words avg

All processes are documented, configurable, and replicable.
