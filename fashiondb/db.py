"""SQLite fashion rules store (#5)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DB = Path("data") / "fashiondb.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL DEFAULT 'json',
  path TEXT
);

CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(id),
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(id),
  external_id TEXT,
  url TEXT,
  title TEXT,
  raw_json TEXT,
  UNIQUE(source_id, external_id)
);

CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(id),
  rule_key TEXT NOT NULL,
  claim TEXT NOT NULL,
  category TEXT,
  formality TEXT,
  confidence REAL,
  polarity TEXT,
  strength TEXT,
  embedding_ref TEXT,
  context_json TEXT,
  source_url TEXT,
  UNIQUE(source_id, rule_key)
);

CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
  claim, category, content='rules', content_rowid='id'
);
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rule_key_for(claim: str, source_url: str | None = None) -> str:
    h = hashlib.sha256()
    h.update((claim or "").strip().lower().encode())
    if source_url:
        h.update(b"|")
        h.update(source_url.strip().encode())
    return h.hexdigest()[:24]


def upsert_source(conn: sqlite3.Connection, slug: str, kind: str = "json", path: str | None = None) -> int:
    conn.execute(
        "INSERT INTO sources (slug, kind, path) VALUES (?, ?, ?) "
        "ON CONFLICT(slug) DO UPDATE SET kind=excluded.kind, path=excluded.path",
        (slug, kind, path),
    )
    row = conn.execute("SELECT id FROM sources WHERE slug=?", (slug,)).fetchone()
    return int(row["id"])


def upsert_rule(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    claim: str,
    category: str | None = None,
    formality: str | None = None,
    confidence: float | None = None,
    polarity: str | None = None,
    strength: str | None = None,
    embedding_ref: str | None = None,
    context: dict[str, Any] | None = None,
    source_url: str | None = None,
    rule_key: str | None = None,
) -> None:
    key = rule_key or rule_key_for(claim, source_url)
    ctx = json.dumps(context or {}, ensure_ascii=False)
    conn.execute(
        """INSERT INTO rules (
             source_id, rule_key, claim, category, formality, confidence,
             polarity, strength, embedding_ref, context_json, source_url
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_id, rule_key) DO UPDATE SET
             claim=excluded.claim,
             category=excluded.category,
             formality=excluded.formality,
             confidence=excluded.confidence,
             polarity=excluded.polarity,
             strength=excluded.strength,
             embedding_ref=excluded.embedding_ref,
             context_json=excluded.context_json,
             source_url=excluded.source_url
        """,
        (
            source_id,
            key,
            claim,
            category,
            formality,
            confidence,
            polarity,
            strength,
            embedding_ref,
            ctx,
            source_url,
        ),
    )


def count_rules(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT count(*) FROM rules").fetchone()[0])


def export_rules_json(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT rule_key AS id, claim, category, polarity, confidence, strength, "
        "context_json, source_url FROM rules ORDER BY id"
    ).fetchall()
    rules = []
    for r in rows:
        item = {
            "id": r["id"],
            "claim": r["claim"],
            "category": r["category"],
            "polarity": r["polarity"],
            "confidence": r["confidence"],
            "strength": r["strength"],
            "source_url": r["source_url"],
            "context": json.loads(r["context_json"] or "{}"),
        }
        rules.append(item)
    return {"rules": rules}
