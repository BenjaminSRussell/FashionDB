"""Wardrobe vs rules checker with CI-friendly JSON report."""
from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


REPORT_SCHEMA = {
    "type": "object",
    "required": ["ok", "wardrobe_path", "rules_source", "checked", "violations"],
    "properties": {
        "ok": {"type": "boolean"},
        "wardrobe_path": {"type": "string"},
        "rules_source": {"type": "string"},
        "checked": {"type": "integer"},
        "violations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item", "rule_id", "message"],
            },
        },
    },
}


@dataclass
class Violation:
    item: str
    rule_id: str
    message: str


def _load_rules_jsonl(path: Path) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "rules" in obj and isinstance(obj["rules"], list):
                rules.extend(obj["rules"])
            else:
                rules.append(obj)
    return rules


def _load_rules_sqlite(path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(path)
    try:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rules'"
        )
        if not cur.fetchone():
            return []
        rows = con.execute(
            "SELECT rule_id, text, categories FROM rules"
        ).fetchall()
        out = []
        for rule_id, text, categories in rows:
            cats = json.loads(categories) if categories else []
            out.append({"rule_id": rule_id, "text": text, "categories": cats})
        return out
    finally:
        con.close()


def load_rules(rules_path: Path) -> list[dict[str, Any]]:
    if rules_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        return _load_rules_sqlite(rules_path)
    if rules_path.suffix.lower() == ".jsonl":
        return _load_rules_jsonl(rules_path)
    # JSON list or digest
    data = json.loads(rules_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "rules" in data:
        return data["rules"]
    raise ValueError(f"Unsupported rules format: {rules_path}")


def load_wardrobe(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _item_blob(row: dict[str, str]) -> str:
    return " ".join(str(v) for v in row.values() if v).lower()


def check_wardrobe(wardrobe_path: Path, rules_path: Path) -> dict[str, Any]:
    rows = load_wardrobe(wardrobe_path)
    rules = load_rules(rules_path)
    violations: list[Violation] = []

    # Lightweight rule: absolute "never"/"forbidden" tokens from rule text
    for row in rows:
        item = row.get("name") or row.get("item") or row.get("title") or json.dumps(row)
        blob = _item_blob(row)
        for rule in rules:
            text = (rule.get("text") or "").lower()
            rid = rule.get("rule_id") or rule.get("id") or "unknown"
            if not text:
                continue
            # Flag wardrobe items that contain a forbidden phrase after "never wear"/"avoid"
            for marker in ("never wear ", "avoid ", "do not wear "):
                if marker in text:
                    phrase = text.split(marker, 1)[1].split(".")[0].strip().rstrip(".")
                    if not phrase:
                        continue
                    tokens = [tok for tok in phrase.replace(",", " ").split() if len(tok) > 2]
                    # Match if most significant tokens appear in the wardrobe item blob
                    if tokens and sum(1 for tok in tokens if tok in blob) >= max(2, len(tokens) - 1):
                        violations.append(
                            Violation(
                                item=str(item),
                                rule_id=str(rid),
                                message=f"Item matches forbidden phrase from rule: {phrase}",
                            )
                        )
    report = {
        "ok": len(violations) == 0,
        "wardrobe_path": str(wardrobe_path),
        "rules_source": str(rules_path),
        "checked": len(rows),
        "violations": [asdict(v) for v in violations],
        "schema": "fashiondb.check.report.v1",
    }
    return report
