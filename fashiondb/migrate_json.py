"""One-shot JSON → SQLite migration (#5)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fashiondb.db import connect, count_rules, upsert_rule, upsert_source


def _load_rules(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rules" in data:
        return list(data["rules"])
    if isinstance(data, list):
        return list(data)
    raise ValueError(f"unrecognized rules JSON shape in {path}")


def migrate_file(conn, path: Path, slug: str) -> int:
    source_id = upsert_source(conn, slug=slug, kind="json", path=str(path))
    n = 0
    for item in _load_rules(path):
        claim = item.get("claim") or item.get("rule_text") or item.get("text")
        if not claim:
            continue
        ctx = item.get("context") if isinstance(item.get("context"), dict) else {}
        formality = item.get("formality") or (ctx.get("dress_code_level") if ctx else None)
        upsert_rule(
            conn,
            source_id=source_id,
            claim=claim,
            category=item.get("category") or item.get("domain"),
            formality=formality,
            confidence=item.get("confidence"),
            polarity=item.get("polarity"),
            strength=item.get("strength"),
            embedding_ref=item.get("embedding_ref"),
            context=ctx,
            source_url=item.get("source_url") or item.get("url"),
            rule_key=item.get("id") or item.get("rule_key"),
        )
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Migrate fashion rules JSON into SQLite")
    ap.add_argument("--db", default=None, help="SQLite path (default data/fashiondb.db)")
    ap.add_argument(
        "paths",
        nargs="*",
        help="JSON files (default: fixtures + Beans sample if present)",
    )
    args = ap.parse_args(argv)
    paths = [Path(p) for p in args.paths]
    if not paths:
        defaults = [
            Path("tests/fixtures/rules_sample.json"),
            Path("Beans/data/fixtures/sample_rules.json"),
            Path("Beans/data/rules.json"),
            Path("data/reddit_fashion_data.json"),
        ]
        paths = [p for p in defaults if p.exists()]
    if not paths:
        print("no JSON inputs found", flush=True)
        return 1
    conn = connect(args.db)
    total = 0
    try:
        for path in paths:
            slug = path.stem.replace(" ", "_")
            n = migrate_file(conn, path, slug)
            total += n
            print(f"migrated {n} rules from {path}")
        conn.commit()
        print(f"db now has {count_rules(conn)} rules")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
