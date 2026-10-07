# FashionDB SQLite schema (#5)

Default path: `data/fashiondb.db`.

## Tables

| Table | Purpose |
|-------|---------|
| `sources` | Provenance (`slug`, `kind`, optional `path`) |
| `scrape_runs` | Append-only scrape/migration runs |
| `posts` | Reddit/source posts keyed by `(source_id, external_id)` |
| `rules` | Fashion rules keyed by `(source_id, rule_key)` — `rule_key` is stable hash of claim(+url) or explicit id |
| `rules_fts` | FTS5 index over rule claim/category for future UI search |

## Commands

```bash
python -m fashiondb migrate-json [paths…]   # load JSON into SQLite
python -m fashiondb export --format json    # optional JSON dump for notebooks
```

Scrapers should call `fashiondb.db.upsert_rule` rather than rewriting whole JSON files. Dedup is by `(source_id, rule_key)` / URL hash, not whole-file replace.
