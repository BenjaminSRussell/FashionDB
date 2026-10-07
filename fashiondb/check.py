"""CI-friendly wardrobe × rules check (#8)."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


REPORT_SCHEMA = {
    "type": "object",
    "required": ["ok", "violations", "checked", "rules_loaded"],
}


def load_rules_sqlite(path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, claim, category, polarity FROM rules"
        ).fetchall()
    except sqlite3.OperationalError:
        # Flexible schema: try rule_text
        rows = conn.execute(
            "SELECT rowid AS id, rule_text AS claim, COALESCE(category,'') AS category, "
            "COALESCE(polarity,'nuanced') AS polarity FROM rules"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def load_rules_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = data.get("rules", data if isinstance(data, list) else [])
    out = []
    for i, r in enumerate(rules):
        out.append(
            {
                "id": r.get("id", str(i)),
                "claim": r.get("claim") or r.get("rule_text") or "",
                "category": r.get("category") or "",
                "polarity": r.get("polarity") or "nuanced",
            }
        )
    return out


def load_wardrobe_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_wardrobe(wardrobe: list[dict[str, str]], rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag negative/absolute rules whose category keywords appear in wardrobe rows."""
    violations = []
    for item in wardrobe:
        blob = " ".join(str(v) for v in item.values()).lower()
        cat = (item.get("category") or item.get("Category") or "").lower()
        for rule in rules:
            polarity = (rule.get("polarity") or "").lower()
            if polarity not in {"negative", "avoid"} and "never" not in (rule.get("claim") or "").lower():
                continue
            claim = (rule.get("claim") or "").lower()
            # crude keyword hit: shared category or claim token in item text
            rule_cat = (rule.get("category") or "").lower()
            if rule_cat and cat and rule_cat != cat:
                continue
            tokens = [t for t in claim.replace(",", " ").split() if len(t) > 3][:6]
            if tokens and sum(1 for t in tokens if t in blob) >= max(1, len(tokens) // 2):
                violations.append(
                    {
                        "item": {k: item.get(k) for k in ("id", "brand", "name", "category") if item.get(k)},
                        "rule_id": rule.get("id"),
                        "claim": rule.get("claim"),
                        "polarity": rule.get("polarity"),
                    }
                )
    # clean empty keys in item
    for v in violations:
        v["item"] = {k: val for k, val in (v["item"] or {}).items() if val is not None}
    return {
        "ok": len(violations) == 0,
        "checked": len(wardrobe),
        "rules_loaded": len(rules),
        "violations": violations,
        "schema": "fashiondb.check.v1",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fashiondb check", description="Check wardrobe CSV against rules")
    p.add_argument("--wardrobe", type=Path, required=True)
    p.add_argument("--rules", type=Path, required=True, help="SQLite .db or rules JSON")
    p.add_argument("--json-report", type=Path, help="Write JSON report path")
    args = p.parse_args(argv)

    if args.rules.suffix in {".db", ".sqlite", ".sqlite3"}:
        rules = load_rules_sqlite(args.rules)
    else:
        rules = load_rules_json(args.rules)
    wardrobe = load_wardrobe_csv(args.wardrobe)
    report = check_wardrobe(wardrobe, rules)
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "violations": len(report["violations"]), "checked": report["checked"]}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
