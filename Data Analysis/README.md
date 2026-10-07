# Data Analysis Project

## 📁 Directory Structure

```
Data Analysis/
├── data/                          # All JSON data files
│   ├── reddit_fashion_data.json   # 64 MB - Reddit fashion posts & comments
│   └── fashion_rules.json         # 257 MB - Fashion rules & articles
│
├── src/                           # All Python code
│   ├── reddit_db_manager.py       # Load Reddit data into Postgres
│   ├── fashion_rules_db_manager.py# Load Fashion Rules data into Postgres
│   ├── check_databases.py         # Quick database status checker
│   └── WRK.py                     # Original analysis script
│
├── DATABASE_GUIDE.md              # Complete database usage guide
├── README.md                      # This file
└── requirements.txt               # Python dependencies
```

## 🚀 Quick Start

### 1. Load Data into Postgres

```bash
# Load Reddit fashion data (creates 'reddit_fashion' database)
python3 src/reddit_db_manager.py

# Load Fashion rules data (creates 'fashion_rules_db' database)
python3 src/fashion_rules_db_manager.py
```

### 2. Check Database Status

```bash
python3 src/check_databases.py
```

### 3. Query the Databases

```bash
# Connect to Reddit database
psql -d reddit_fashion

# Connect to Fashion Rules database
psql -d fashion_rules_db
```

## 📊 Databases

### reddit_fashion
- **Structure:** Relational tables (posts, comments)
- **Posts:** 19,715
- **Comments:** 166,291
- **Categories:** 22 subreddits

### fashion_rules_db
- **Structure:** JSONB document
- **Size:** 253 MB
- **Keys:** articles, metadata, all_rules, article_content, organized_rules, outfit_formulas, quick_reference

## 📖 Documentation

See [DATABASE_GUIDE.md](DATABASE_GUIDE.md) for:
- Detailed query examples
- Database schemas
- Tips & tricks

## 🔄 Re-running Setup

All database manager scripts are idempotent - you can run them multiple times safely. They will:
1. Create database (if needed)
2. Create tables
3. Clear existing data
4. Load fresh data from JSON files
5. Show statistics

## 🗂️ Data Directory

All JSON files are stored in the `data/` directory to keep code and data separate. All scripts automatically reference this directory.

## Rule schema

Extractor output should match `src/standardization/schema.json`.
Validate locally:

```bash
pytest "Data Analysis/tests/test_schema_validate.py" -q
```
