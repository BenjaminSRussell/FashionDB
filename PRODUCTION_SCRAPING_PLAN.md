# Production Scraping Plan

**Status:** Ready for Production
**Date:** 2025-11-07

---

## ✅ What's Ready

### Scrapers Built
1. **StyleForum Scraper** - ✅ Tested & Working
   - Forum thread scraping
   - Extracts posts, replies, tags
   - Rate-limited and respectful

2. **PutThisOn Scraper** - ✅ Tested & Working
   - Blog article scraping
   - Extracts full content, author, metadata
   - Handles their specific HTML structure

3. **Enhanced Blog Scraper** - ✅ Built
   - Generic scraper with per-site configuration
   - Supports site-specific headers (Cloudflare bypass, etc.)
   - Configurable rate limiting
   - Handles WordPress, Shopify, custom sites

4. **Production Orchestrator** - ✅ Built
   - Routes to appropriate scraper per domain
   - Stores in SQLite database
   - Logs all attempts
   - Handles errors gracefully

### Data Sources Identified

**Curated Sites (15 high-quality sources):**
- Articles of Style (87+ posts)
- Parisian Gentleman (42 posts)
- Black Lapel / The Compass (63 posts)
- Glen Palmer Style (28 posts)
- Kinowear (19 manufacturer posts)
- Lisbon Suit Company (34 European fit posts)
- Perfect Gentleman (26 traditional posts)
- Image Granted (47 professional posts)
- Style & Shaving (31 grooming+style posts)
- Suitable Wardrobe (34 minimalist posts)
- The Modest Guy (42 budget posts)
- Sharpography (29 technical posts)
- Bespoke Post Journal (56 practical guides)
- A Tailored Suit (38 formal wear posts)
- The Armoury Journal (15 bespoke guides)

**Reddit-Discovered Sites (7 sources with confirmed URLs):**
- PutThisOn.com (50 URLs, 66 mentions)
- StyleForum.net (50 URLs, 53 mentions)
- Dappered.com (25 URLs, 25 mentions)
- StreetXSprezza WordPress (21 URLs, 24 mentions)
- Medium.com (7 URLs, 8 mentions)
- NStarLeather WordPress (5 URLs, 7 mentions)
- TheShoeSnobBlog (4 URLs, 4 mentions)

**Total Ready to Scrape:**
- 22 unique domains
- 193 confirmed URLs
- Estimated 500+ additional posts discoverable

---

## 📊 Estimated Content Yield

### Conservative Estimates

**Curated Sites:**
- 15 sites × ~40 posts avg = **600 posts**
- Average post length: 2,000-5,000 words
- Quality: Very high (expert-written, edited content)

**Reddit-Discovered:**
- 193 known URLs = **193 posts**
- Can discover ~300 more via category pages
- Total: ~500 posts from discovered sites

**Grand Total:**
- ~1,100 high-quality blog posts and forum threads
- Estimated **150,000-200,000 rules** extractable
- Quality significantly higher than Reddit

---

## 🎯 Scraping Strategy

### Phase 1: Test Run (Today)
- Scrape 5 curated sites (top priority)
- Scrape 2 Reddit-discovered sites (PutThisOn, StyleForum)
- Validate data quality
- Estimated: ~100 posts, ~10,000 rules

### Phase 2: Full Curated Scrape (This Week)
- Scrape all 15 curated sites
- Full depth (all category pages)
- Estimated: ~600 posts, ~80,000 rules

### Phase 3: Reddit-Discovered Scrape (Next Week)
- Scrape all 7 discovered sites
- Follow pagination to find more content
- Estimated: ~500 posts, ~70,000 rules

### Phase 4: Expansion (Ongoing)
- Monitor for new sources
- Periodic re-scraping for updates
- Add sources as discovered

---

## 🛡️ Scraping Best Practices

### Rate Limiting
- Each site has configured delay (0.7s - 2.5s)
- Never exceed 1 request per second per site
- Respect robots.txt
- Use polite User-Agent string

### Error Handling
- 3 retry attempts with exponential backoff
- Log all failures for manual review
- Skip problematic posts, don't halt entire scrape
- Alert on repeated failures from same domain

### Data Quality
- Minimum 300 chars body content
- Must have valid title
- Prefer posts with author and date
- Flag content that seems auto-generated

### Storage
- SQLite database for scraped content
- Separate scraping log for monitoring
- JSON backup of raw scraped data
- Regular database maintenance (VACUUM)

---

## 📁 Database Schema

```sql
-- Scraped content
CREATE TABLE scraped_content (
    content_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,           -- e.g., "articlesofstyle.com"
    source_type TEXT,                -- "blog", "forum", "article"
    title TEXT,
    url TEXT UNIQUE,
    body TEXT,                       -- Main content
    author TEXT,
    published_date TEXT,
    score INTEGER DEFAULT 0,
    scraped_at TIMESTAMP,
    metadata TEXT                    -- JSON: tags, images, etc.
);

-- Scraping log
CREATE TABLE scraping_log (
    id INTEGER PRIMARY KEY,
    source TEXT,
    url TEXT,
    success BOOLEAN,
    error_message TEXT,
    scraped_at TIMESTAMP
);
```

---

## 🔧 Configuration Files

### `scrapers/curated_sites.json`
Contains 15 curated sites with:
- Site name and domain
- Category URLs to scrape
- Rate limit delay
- Priority (1-10)
- Scraping analysis notes (headers, bypasses, etc.)

### `data/scraping_queue.json`
Generated from:
- Curated sites configuration
- Reddit-discovered URLs
- Organized by priority and mentions
- Ready-to-use URL lists

---

## 🚀 Running Production Scrape

### Test Run (Recommended First Step)
```bash
# Test on 1-2 sites first
python3 scrapers/production_scraper.py

# This will:
# 1. Load top 5 curated sites
# 2. Scrape 10 posts per category
# 3. Save to data/scraped_content.db
# 4. Generate logs
```

### Full Production Run
```bash
# Edit production_scraper.py and remove the [:5] limit
# Then run full scrape
python3 scrapers/production_scraper.py

# Monitor progress in real-time
tail -f data/scraping.log
```

### Check Results
```bash
# Query database
sqlite3 data/scraped_content.db

# Count scraped content
SELECT source, COUNT(*) as posts
FROM scraped_content
GROUP BY source
ORDER BY posts DESC;

# View recent scrapes
SELECT title, source, LENGTH(body) as chars
FROM scraped_content
ORDER BY scraped_at DESC
LIMIT 20;
```

---

## 📈 Expected Results

### After Phase 1 (Test Run)
- **Sources scraped:** 7
- **Posts collected:** ~100
- **Est. rules extractable:** ~10,000
- **Database size:** ~5MB
- **Time:** ~1-2 hours

### After Phase 2 (Curated Sites)
- **Sources scraped:** 15
- **Posts collected:** ~600
- **Est. rules extractable:** ~80,000
- **Database size:** ~25MB
- **Time:** ~6-8 hours

### After Phase 3 (All Sources)
- **Sources scraped:** 22
- **Posts collected:** ~1,100
- **Est. rules extractable:** ~150,000-200,000
- **Database size:** ~45MB
- **Time:** ~12-15 hours total

---

## 🔍 Quality Validation

### Automated Checks
- Minimum body length: 300 chars
- Title present and non-empty
- URL accessible and matches domain
- No duplicate content_ids
- Reasonable char count (not truncated)

### Manual Spot Checks
- Sample 20 random posts
- Verify content extraction accuracy
- Check for formatting issues
- Validate author/date extraction

### Quality Metrics
- **Success rate:** Target >85%
- **Avg body length:** Target >2,000 chars
- **With author:** Target >60%
- **With date:** Target >70%

---

## 🎯 Integration with Rule Extraction

### After Scraping Complete
1. **Process with Ollama:**
   ```bash
   python3 standardization/ollama.py \
     --input data/scraped_content.db \
     --output data/extracted_rules.jsonl
   ```

2. **Combine with Reddit Rules:**
   - Merge scraped content rules with Reddit rules
   - Deduplicate based on semantic similarity
   - Create master rules database

3. **Quality Filtering:**
   - Filter for confidence >0.65
   - Remove obvious duplicates
   - Categorize by topic

---

## 🚨 Potential Issues & Solutions

### Issue: Site Blocks Scraper
**Solution:**
- Check robots.txt compliance
- Increase delay between requests
- Rotate User-Agent if needed
- Use site-specific headers from config

### Issue: Content Extraction Fails
**Solution:**
- Inspect HTML structure manually
- Update scraper selectors
- Log problematic URLs for manual review
- Build site-specific scraper if needed

### Issue: Rate Limited
**Solution:**
- Increase delay in configuration
- Scrape during off-peak hours
- Split across multiple days
- Implement exponential backoff

### Issue: Database Locks
**Solution:**
- Use WAL mode: `PRAGMA journal_mode=WAL`
- Don't run multiple scrapers concurrently
- Regular VACUUM operations

---

## 📊 Monitoring & Reporting

### Real-Time Monitoring
```bash
# Watch scraping progress
watch -n 5 'sqlite3 data/scraped_content.db "SELECT COUNT(*) FROM scraped_content"'

# Check error rate
sqlite3 data/scraped_content.db \
  "SELECT success, COUNT(*) FROM scraping_log GROUP BY success"
```

### Post-Scrape Analysis
```bash
# Generate scraping report
python3 tools/analyze_scraping_results.py

# View quality metrics
python3 tools/validate_scraped_content.py
```

---

## ✅ Checklist Before Production Run

- [x] Curated sites configuration loaded
- [x] Reddit-discovered URLs prepared
- [x] Scrapers tested on sample URLs
- [x] Database schema created
- [x] Rate limiting configured
- [x] Error handling implemented
- [x] Logging configured
- [ ] Test run completed successfully
- [ ] Spot-check quality validates
- [ ] Ready for full production run

---

## 🎉 Summary

**We're ready to scrape!**

- ✅ 22 high-quality sources identified
- ✅ Custom scrapers built and tested
- ✅ Production pipeline ready
- ✅ 193 confirmed URLs queued
- ✅ Estimated 150K-200K rules achievable

**Next Step:** Run test scrape on top 5 sites to validate pipeline.

---

**Ready to harvest the beans!** 🌱→🫘
